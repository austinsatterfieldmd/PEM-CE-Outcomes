"""
Disease Classifier - Stage 1 of two-stage tagging architecture.

This module provides combined oncology gate + disease state classification from clinical questions.
Uses 3-model voting (GPT-5.2, Claude Opus 4.5, Gemini 2.5 Pro) for robust classification.
"""

import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class DiseaseClassifier:
    """
    Stage 1: Combined oncology gate + disease state detection with 3-model voting.

    Performs two classifications:
    1. is_oncology: Is this an oncology/hematologic malignancy question?
    2. disease_state: If oncology, what is the primary cancer type?

    Uses 3-model parallel voting (GPT-5.2, Claude, Gemini) with optional web search
    fallback for trial-based inference.
    """

    # Models to use for voting (2-model: GPT-5.2 + Gemini 2.5 Pro)
    # Claude dropped for cost savings - comparable accuracy, higher cost
    VOTING_MODELS = ["gpt", "gemini"]

    def __init__(self, client, use_voting: bool = True):
        """
        Initialize the disease classifier.

        Args:
            client: OpenRouterClient instance for LLM calls
            use_voting: If True, use 3-model voting. If False, use single model (claude).
        """
        self.client = client
        self.use_voting = use_voting
        self.prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load the disease classifier prompt from file."""
        prompt_path = Path("prompts/v2.0/disease_classifier_prompt.txt")

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Disease classifier prompt not found at {prompt_path}"
            )

        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    async def classify(
        self,
        question_text: str,
        correct_answer: Optional[str] = None,
        activity_names: Optional[List[str]] = None,
        start_dates: Optional[List[str]] = None,
        incorrect_answers: Optional[List[str]] = None
    ) -> Dict[str, Union[bool, Optional[str], Dict]]:
        """
        Classify oncology status and disease state from a question.

        Args:
            question_text: The question text
            correct_answer: The correct answer text (optional but recommended)
            activity_names: List of activity/course titles where this question appeared
                           (provides context - e.g., "Miami Breast Cancer Conference" implies breast cancer)
            start_dates: List of activity start dates (YYYY-MM-DD format)
            incorrect_answers: List of incorrect answer options (provides additional context)

        Returns:
            {
                "is_oncology": True/False,
                "disease_state": "Breast cancer",  # or null if non-oncology or not determined
                "needs_review": True/False,  # True if any disagreement (for LLM eval)
                "review_reason": "conflict" | "majority" | "web_search_used" | null,
                "voting_details": {  # Only present if use_voting=True
                    "gpt": {"is_oncology": True, "disease_state": "Breast cancer"},
                    "claude": {"is_oncology": True, "disease_state": "Breast cancer"},
                    "gemini": {"is_oncology": True, "disease_state": "Breast cancer"},
                    "web_search": {"disease_state": "Breast cancer", "source": "trial_lookup"},  # if used
                    "agreement": "unanimous"  # or "majority" or "conflict"
                }
            }
        """
        # Build prompt with question context
        messages = self._build_messages(
            question_text, correct_answer, activity_names, start_dates, incorrect_answers
        )

        if self.use_voting:
            # 2-model voting (GPT-5.2 + Gemini 2.5 Pro)
            logger.info("Classifying with 2-model voting (GPT-5.2, Gemini)")
            result = await self._classify_with_voting(messages, question_text, correct_answer)
        else:
            # Single model (fallback)
            logger.info("Classifying with single model (claude)")
            result = await self._classify_single(messages, "claude")
            # Single model mode: no voting, so no review needed unless missing data
            result["needs_review"] = result.get("disease_state") is None and result.get("is_oncology", False)
            result["review_reason"] = "single_model_uncertain" if result["needs_review"] else None

        # Ensure is_oncology field exists (fallback to keyword detection)
        if "is_oncology" not in result:
            logger.warning("Response missing is_oncology, using keyword fallback")
            result["is_oncology"] = self._detect_oncology_keywords(
                question_text, correct_answer or ""
            )
            # Mark for review since we had to use fallback
            result["needs_review"] = True
            result["review_reason"] = "keyword_fallback_used"

        # If not oncology, disease_state must be null
        if not result.get("is_oncology"):
            result["disease_state"] = None
            # Non-oncology unanimous agreement doesn't need review
            if result.get("voting_details", {}).get("agreement") == "unanimous":
                result["needs_review"] = False
                result["review_reason"] = None
            logger.info("Question classified as non-oncology")
            return result

        # NOTE: Web search fallback disabled for Stage 1
        # The 3-model voting achieves 97% unanimous agreement, and web search was:
        # 1. Incorrectly identifying biomarkers/staging as trial names (HER2, PD-L1, T3, etc.)
        # 2. Returning inaccurate disease mappings for actual trials
        # Will revisit with a static trial->disease lookup table if needed after few-shot iteration.
        #
        # For now, just log disagreements for review without web search
        agreement = result.get("voting_details", {}).get("agreement", "")
        if agreement in ["majority", "conflict"]:
            logger.info(f"Stage 1 disagreement (agreement={agreement}) - flagged for manual review")

        return result

    async def _classify_with_voting(
        self,
        messages: List[Dict],
        question_text: str,
        correct_answer: Optional[str]
    ) -> Dict[str, Union[bool, Optional[str], Dict]]:
        """
        Classify using 3-model parallel voting.

        Returns aggregated result with voting details.
        """
        # Call all 3 models in parallel
        responses = await self.client.generate_parallel(
            messages=messages,
            models=self.VOTING_MODELS,
            temperature=0.0  # Deterministic classification
        )

        # Parse responses from each model
        model_results = {}
        failed_models = []

        for model in self.VOTING_MODELS:
            response = responses.get(model, {})
            content = response.get("content", "")

            if response.get("error"):
                logger.error(f"Error from {model}: {response.get('error')}")
                model_results[model] = {"is_oncology": None, "disease_state": None, "error": response.get("error")}
                failed_models.append(model)
            elif not content or not content.strip():
                # Empty response - treat as error
                logger.error(f"Empty response from {model}")
                model_results[model] = {"is_oncology": None, "disease_state": None, "error": "Empty response"}
                failed_models.append(model)
            else:
                parsed = self._parse_json_response(content)
                # Check if parse was successful (must have is_oncology)
                if "is_oncology" not in parsed:
                    logger.error(f"Failed to parse is_oncology from {model} response: {content[:200]}")
                    model_results[model] = {"is_oncology": None, "disease_state": None, "error": "Parse failed - no is_oncology"}
                    failed_models.append(model)
                else:
                    model_results[model] = parsed

        # Retry failed models once (helps recover from transient parse failures)
        if failed_models:
            logger.info(f"Retrying {len(failed_models)} failed model(s): {failed_models}")
            import asyncio
            await asyncio.sleep(1)  # Brief delay before retry

            retry_responses = await self.client.generate_parallel(
                messages=messages,
                models=failed_models,
                temperature=0.0
            )

            for model in failed_models:
                response = retry_responses.get(model, {})
                content = response.get("content", "")

                if response.get("error"):
                    logger.error(f"Retry error from {model}: {response.get('error')}")
                    # Keep original error
                elif not content or not content.strip():
                    logger.error(f"Retry empty response from {model}")
                    # Keep original error
                else:
                    parsed = self._parse_json_response(content)
                    if "is_oncology" in parsed:
                        logger.info(f"Retry successful for {model}")
                        model_results[model] = parsed
                    else:
                        logger.error(f"Retry parse failed for {model}")

        # Aggregate votes
        result = self._aggregate_votes(model_results, question_text, correct_answer)

        return result

    def _aggregate_votes(
        self,
        model_results: Dict[str, Dict],
        question_text: str,
        correct_answer: Optional[str]
    ) -> Dict[str, Union[bool, Optional[str], Dict]]:
        """
        Aggregate votes from 2 models (GPT + Gemini).

        GPT is the default when models disagree or Gemini fails.
        All disagreements are flagged for review but have a value assigned.

        For is_oncology: Both must agree, conflict uses GPT's answer + flags for review
        For disease_state: Both must agree, conflict uses GPT's answer + flags for review

        Returns needs_review=True for any disagreement.

        Distinguishes between:
        - "unanimous": Both models agree (2/2)
        - "conflict": Models disagree (1/1) - uses GPT as default
        - "partial_response": 1 model had SSL/API error - uses GPT if available
        """
        # Track how many models responded successfully vs had errors
        successful_models = []
        error_models = []

        for model, result in model_results.items():
            if result.get("error"):
                error_models.append(model)
            elif result.get("is_oncology") is not None:
                successful_models.append(model)
            # Note: If is_oncology is None but no error, model returned unparseable response

        models_with_errors = len(error_models)
        models_responded = len(successful_models)

        # Collect votes
        oncology_votes = []
        disease_votes = []

        for model, result in model_results.items():
            if result.get("is_oncology") is not None:
                oncology_votes.append(result["is_oncology"])
            if result.get("disease_state"):
                disease_votes.append(result["disease_state"])

        # Track review status
        needs_review = False
        review_reason = None

        # Determine is_oncology by 2-model consensus
        if oncology_votes:
            true_count = sum(1 for v in oncology_votes if v is True)
            false_count = sum(1 for v in oncology_votes if v is False)

            if true_count == 2:
                # Both models agree: oncology
                is_oncology = True
                agreement_onc = "unanimous"
            elif false_count == 2:
                # Both models agree: non-oncology
                is_oncology = False
                agreement_onc = "unanimous"
            elif len(oncology_votes) == 2:
                # 1/1 split - use GPT's answer as default, but flag for review
                gpt_result = model_results.get('gpt', {})
                is_oncology = gpt_result.get('is_oncology')
                agreement_onc = "conflict"
                needs_review = True
                review_reason = "oncology_conflict"
                logger.warning(f"Oncology conflict - using GPT's answer ({is_oncology}), flagging for review")
            elif len(oncology_votes) == 1:
                # Only 1 vote - prefer GPT if available, else use whatever we have
                gpt_result = model_results.get('gpt', {})
                if gpt_result.get('is_oncology') is not None:
                    is_oncology = gpt_result.get('is_oncology')
                else:
                    is_oncology = oncology_votes[0]
                agreement_onc = "partial_response"
                needs_review = True
                review_reason = "single_model_vote"
            else:
                # Edge case: shouldn't happen with 2 models
                is_oncology = None
                agreement_onc = "conflict"
                needs_review = True
                review_reason = "oncology_conflict"
        else:
            # No valid votes - flag for review, don't use fallback automatically
            is_oncology = None
            agreement_onc = "no_votes"
            needs_review = True
            review_reason = "no_oncology_votes"
            logger.warning("No valid oncology votes received, flagging for review")

        # Determine disease_state by majority vote (only if oncology)
        disease_state = None
        agreement_disease = "n/a"

        if is_oncology and disease_votes:
            disease_counter = Counter(disease_votes)
            most_common = disease_counter.most_common()

            if most_common:
                top_disease, top_count = most_common[0]

                if top_count == 2:
                    # Both models agree on disease
                    disease_state = top_disease
                    agreement_disease = "unanimous"
                elif len(disease_votes) == 2 and len(most_common) > 1:
                    # 1/1 split - check for normalization (e.g., "Breast cancer" vs "breast cancer")
                    normalized = self._normalize_disease_votes(disease_votes)
                    norm_counter = Counter(normalized)
                    norm_most_common = norm_counter.most_common()

                    if norm_most_common and norm_most_common[0][1] == 2:
                        # Both agree after normalization
                        disease_state = norm_most_common[0][0]
                        agreement_disease = "unanimous_normalized"
                    else:
                        # True conflict - use GPT's answer as default, but flag for review
                        gpt_result = model_results.get('gpt', {})
                        disease_state = gpt_result.get('disease_state')
                        agreement_disease = "conflict"
                        needs_review = True
                        review_reason = review_reason or "disease_conflict"
                        logger.warning(f"Disease state conflict - using GPT's answer ({disease_state}), flagging for review")
                elif len(disease_votes) == 1:
                    # Only 1 vote - prefer GPT if available, else use whatever we have
                    gpt_result = model_results.get('gpt', {})
                    if gpt_result.get('disease_state'):
                        disease_state = gpt_result.get('disease_state')
                    else:
                        disease_state = top_disease
                    agreement_disease = "partial_response"
                    needs_review = True
                    review_reason = review_reason or "single_disease_vote"
                else:
                    # Single unique vote from 2 models (edge case)
                    disease_state = top_disease
                    agreement_disease = "unanimous"
        elif is_oncology:
            # Oncology but no disease votes - flag for review
            needs_review = True
            review_reason = review_reason or "no_disease_votes"

        # Determine overall agreement level for 2-model voting
        has_model_errors = models_with_errors > 0

        if agreement_onc in ["unanimous"] and agreement_disease in ["unanimous", "unanimous_normalized", "n/a"]:
            if has_model_errors:
                # Both responding models agree, but one had SSL error
                overall_agreement = "partial_response"
                needs_review = True
                review_reason = review_reason or "ssl_error"
            else:
                overall_agreement = "unanimous"
        elif agreement_onc == "conflict" or agreement_disease == "conflict":
            overall_agreement = "conflict"
        elif agreement_onc == "partial_response" or agreement_disease == "partial_response":
            overall_agreement = "partial_response"
        else:
            overall_agreement = "partial"

        return {
            "is_oncology": is_oncology,
            "disease_state": disease_state,
            "needs_review": needs_review,
            "review_reason": review_reason,
            "voting_details": {
                **model_results,
                "agreement": overall_agreement,
                "oncology_agreement": agreement_onc,
                "disease_agreement": agreement_disease,
                "models_responded": models_responded,
                "models_with_errors": models_with_errors,
                "error_models": error_models
            }
        }

    def _normalize_disease_votes(self, votes: List[str]) -> List[str]:
        """
        Normalize disease state votes for comparison.

        Handles case differences and common variations.
        """
        # Normalization map (lowercase -> canonical)
        normalization_map = {
            "breast cancer": "Breast cancer",
            "nsclc": "NSCLC",
            "non-small cell lung cancer": "NSCLC",
            "sclc": "SCLC",
            "small cell lung cancer": "SCLC",
            "crc": "CRC",
            "colorectal cancer": "CRC",
            "colon cancer": "CRC",
            "multiple myeloma": "Multiple myeloma",
            "mm": "Multiple myeloma",
            "prostate cancer": "Prostate cancer",
            "rcc": "RCC",
            "renal cell carcinoma": "RCC",
            "hcc": "HCC",
            "hepatocellular carcinoma": "HCC",
            "melanoma": "Melanoma",
            "dlbcl": "DLBCL",
            "diffuse large b-cell lymphoma": "DLBCL",
            "ovarian cancer": "Ovarian cancer",
            "pancreatic cancer": "Pancreatic cancer",
            "gvhd": "GVHD",
            "graft-versus-host disease": "GVHD",
            "aml": "AML",
            "acute myeloid leukemia": "AML",
            "all": "ALL",
            "acute lymphoblastic leukemia": "ALL",
            "cll": "CLL",
            "chronic lymphocytic leukemia": "CLL",
            "cml": "CML",
            "chronic myeloid leukemia": "CML",
            "hodgkin lymphoma": "Hodgkin lymphoma",
            "hl": "Hodgkin lymphoma",
            "nhl": "NHL",
            "non-hodgkin lymphoma": "NHL",
            "pan-tumor": "Pan-tumor",
            "pan tumor": "Pan-tumor",
            # Umbrella tags (canonical lowercase after first word)
            "heme malignancies": "Heme malignancies",
            "hematologic malignancies": "Heme malignancies",
            "gi cancers": "GI cancers",
            "gastrointestinal cancers": "GI cancers",
            "gyn cancers": "Gyn cancers",
            "gynecologic cancers": "Gyn cancers",
            # Head & neck (canonical lowercase 'n')
            "head & neck": "Head & neck",
            "head and neck": "Head & neck",
            "hnscc": "Head & neck",
        }

        normalized = []
        for vote in votes:
            if vote:
                lower = vote.lower().strip()
                if lower in normalization_map:
                    normalized.append(normalization_map[lower])
                else:
                    # Keep original but title case
                    normalized.append(vote.strip())

        return normalized

    async def _classify_single(
        self,
        messages: List[Dict],
        model: str
    ) -> Dict[str, Union[bool, Optional[str]]]:
        """Classify using a single model (fallback mode)."""
        try:
            response = await self.client.generate(
                messages=messages,
                model=model,
                temperature=0.0
            )

            content = response.get("content", "")
            parsed = self._parse_json_response(content)

            return parsed

        except Exception as e:
            logger.error(f"Error calling {model} for disease classification: {e}")
            return {"disease_state": None}

    def _build_messages(
        self,
        question_text: str,
        correct_answer: Optional[str] = None,
        activity_names: Optional[List[str]] = None,
        start_dates: Optional[List[str]] = None,
        incorrect_answers: Optional[List[str]] = None
    ) -> list:
        """Build messages for LLM call."""
        messages = [
            {"role": "system", "content": self.prompt}
        ]

        # Build user message with all available context
        user_content = f"Question: {question_text}\n"

        if correct_answer:
            user_content += f"\nCorrect Answer: {correct_answer}\n"

        # Add incorrect answers if available
        if incorrect_answers:
            user_content += "\nIncorrect Answer Options:\n"
            for i, ans in enumerate(incorrect_answers, 1):
                if ans and str(ans).strip():
                    user_content += f"  - {ans}\n"

        # Add activity names (can provide disease context clues)
        if activity_names:
            if len(activity_names) == 1:
                user_content += f"\nActivity Name: {activity_names[0]}\n"
            else:
                user_content += f"\nActivities where this question appeared ({len(activity_names)} total):\n"
                for activity in activity_names:
                    user_content += f"  - {activity}\n"

        # Add start dates if available
        if start_dates:
            if len(start_dates) == 1:
                user_content += f"\nActivity Start Date: {start_dates[0]}\n"
            else:
                # Just show the range
                sorted_dates = sorted(start_dates)
                user_content += f"\nDate Range: {sorted_dates[0]} to {sorted_dates[-1]}\n"

        messages.append({"role": "user", "content": user_content})

        return messages

    def _parse_json_response(self, content: str) -> Dict[str, Union[bool, Optional[str]]]:
        """
        Parse JSON response from LLM.

        Handles responses with or without markdown code blocks, including
        cases where the JSON is embedded within explanatory text.

        Returns:
            {
                "is_oncology": True/False (may be missing, caller should use fallback)
                "disease_state": str or None
            }
        """
        content = content.strip()

        # Strategy 1: Try to extract JSON from markdown code block anywhere in response
        # This handles cases like: "Looking at this question...\n```json\n{...}\n```"
        json_block_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
        json_match = re.search(json_block_pattern, content)

        if json_match:
            json_str = json_match.group(1).strip()
            try:
                parsed = json.loads(json_str)
                result = {}
                if "is_oncology" in parsed:
                    result["is_oncology"] = bool(parsed["is_oncology"])
                result["disease_state"] = parsed.get("disease_state")
                result["disease_state_secondary"] = parsed.get("disease_state_secondary")
                return result
            except json.JSONDecodeError:
                pass  # Fall through to other strategies

        # Strategy 2: Try to find raw JSON object in content (no code block)
        # Look for { ... } pattern
        json_object_pattern = r'\{[^{}]*"is_oncology"[^{}]*\}'
        json_obj_match = re.search(json_object_pattern, content)

        if json_obj_match:
            json_str = json_obj_match.group(0)
            try:
                parsed = json.loads(json_str)
                result = {}
                if "is_oncology" in parsed:
                    result["is_oncology"] = bool(parsed["is_oncology"])
                result["disease_state"] = parsed.get("disease_state")
                result["disease_state_secondary"] = parsed.get("disease_state_secondary")
                return result
            except json.JSONDecodeError:
                pass  # Fall through

        # Strategy 3: If content starts with code block (original behavior)
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        try:
            parsed = json.loads(content)
            result = {}
            if "is_oncology" in parsed:
                result["is_oncology"] = bool(parsed["is_oncology"])
            result["disease_state"] = parsed.get("disease_state")
            result["disease_state_secondary"] = parsed.get("disease_state_secondary")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Content: {content[:500]}")  # Truncate for readability
            return {"disease_state": None, "disease_state_secondary": None}

    def _extract_trial_name(self, question_text: str) -> Optional[str]:
        """
        Extract clinical trial name from question text.

        Looks for patterns like:
        - KEYNOTE-756
        - CheckMate-227
        - DESTINY-Breast03
        - IMpower150
        - FLAURA, CROWN (single-word trials)

        Returns:
            Trial name if found, None otherwise
        """
        # Pattern 1: Trials with hyphens (e.g., KEYNOTE-756, CheckMate-227)
        hyphen_pattern = r'\b([A-Z][A-Za-z]*-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\b'
        hyphen_matches = re.findall(hyphen_pattern, question_text)

        if hyphen_matches:
            trial_name = hyphen_matches[0]
            logger.info(f"Extracted trial name (hyphenated): {trial_name}")
            return trial_name

        # Pattern 2: Trials with numbers (e.g., IMpower150, SOLO1, MONARCH3)
        alphanumeric_pattern = r'\b([A-Z][A-Za-z]*\d+)\b'
        alphanumeric_matches = re.findall(alphanumeric_pattern, question_text)

        if alphanumeric_matches:
            trial_name = alphanumeric_matches[0]
            logger.info(f"Extracted trial name (alphanumeric): {trial_name}")
            return trial_name

        # Pattern 3: Single-word all-caps trial names (e.g., FLAURA, CROWN)
        single_word_pattern = r'\b([A-Z]{5,})\b'
        single_matches = re.findall(single_word_pattern, question_text)

        # Filter out common non-trial acronyms (disease names, drug classes, etc.)
        excluded = {
            # Disease names
            "NSCLC", "SCLC", "DLBCL", "GVHD",
            # Drug classes
            "EGFR", "HER2",
            # Trial prefixes (we want the full name, not just the prefix)
            "KEYNOTE", "CHECKMATE", "DESTINY", "IMPOWER"
        }
        single_matches = [m for m in single_matches if m not in excluded]

        if single_matches:
            trial_name = single_matches[0]
            logger.info(f"Extracted trial name (single-word): {trial_name}")
            return trial_name

        return None

    async def _search_trial_disease(self, trial_name: str) -> Optional[str]:
        """
        Use web search to identify disease from trial name.

        Args:
            trial_name: Clinical trial name (e.g., "KEYNOTE-756")

        Returns:
            Disease name if found, None otherwise
        """
        try:
            # Build search query
            query = f"{trial_name} oncology clinical trial disease cancer"

            logger.info(f"Searching for disease via web search: {query}")

            # Use client's web search capability
            search_result = await self.client.web_search(
                query=query,
                context=f"Looking up disease for clinical trial {trial_name}"
            )

            # Parse disease from search result
            content = search_result.get("content", "") if isinstance(search_result, dict) else str(search_result)
            disease = self._parse_disease_from_search(content, trial_name)

            return disease

        except Exception as e:
            logger.error(f"Web search failed for trial {trial_name}: {e}")
            return None

    def _parse_disease_from_search(
        self,
        search_result: str,
        trial_name: str
    ) -> Optional[str]:
        """
        Parse disease name from web search result.

        Looks for canonical disease names in search result text.
        """
        if not search_result:
            return None

        # List of canonical disease names to search for (from constants)
        canonical_diseases = [
            "Breast cancer", "NSCLC", "SCLC", "CRC", "Prostate cancer",
            "Bladder cancer", "RCC", "Ovarian cancer", "Endometrial cancer",
            "Melanoma", "Head & neck", "HCC", "Pancreatic cancer",
            "Cholangiocarcinoma", "Esophagogastric cancer", "Cervical cancer",
            "Uterine cancer", "Sarcoma", "Multiple myeloma", "DLBCL", "FL",
            "MCL", "PTCL", "NHL", "CLL", "AML", "ALL", "CML", "Glioma",
            "GIST", "Merkel cell carcinoma", "Mesothelioma"
        ]

        search_lower = search_result.lower()

        # Check for each canonical disease (case-insensitive)
        for disease in canonical_diseases:
            if disease.lower() in search_lower:
                logger.info(f"Found disease '{disease}' for trial {trial_name}")
                return disease

        # Check for common abbreviations
        abbreviation_map = {
            "mbc": "Breast cancer",
            "metastatic breast": "Breast cancer",
            "triple-negative": "Breast cancer",
            "tnbc": "Breast cancer",
            "non-small cell lung": "NSCLC",
            "small cell lung": "SCLC",
            "colorectal": "CRC",
            "mcrpc": "Prostate cancer",
            "renal cell": "RCC",
            "hepatocellular": "HCC",
            "multiple myeloma": "Multiple myeloma",
            "diffuse large b-cell": "DLBCL",
            "glioblastoma": "Glioma"
        }

        for abbrev, disease in abbreviation_map.items():
            if abbrev in search_lower:
                logger.info(f"Found disease '{disease}' via abbreviation for trial {trial_name}")
                return disease

        logger.warning(f"Could not parse disease from search result for trial {trial_name}")
        return None

    def _detect_oncology_keywords(self, question: str, answer: str) -> bool:
        """
        Fallback keyword detection for oncology classification.

        Used when LLM response doesn't include is_oncology field or votes are tied.

        Args:
            question: The question text
            answer: The correct answer text

        Returns:
            True if oncology keywords detected, False otherwise
        """
        text = f"{question} {answer}".lower()

        # Strong oncology indicators
        oncology_keywords = [
            # Cancer terms
            "cancer", "tumor", "tumour", "malignancy", "malignant",
            "carcinoma", "sarcoma", "adenocarcinoma", "squamous cell",
            # Hematologic malignancies
            "leukemia", "leukaemia", "lymphoma", "myeloma",
            "hodgkin", "non-hodgkin",
            # Specific cancers
            "melanoma", "glioma", "glioblastoma", "mesothelioma",
            "neuroblastoma", "retinoblastoma",
            # Cancer-related terms
            "oncolog", "metasta", "metastatic", "stage iv", "stage iii",
            "chemotherapy", "immunotherapy", "targeted therapy",
            "checkpoint inhibitor", "pd-1", "pd-l1", "ctla-4",
            "car-t", "car t", "bispecific",
            # GVHD
            "gvhd", "graft-versus-host", "graft versus host",
            # Transplant complications in oncology (HSCT/BMT)
            "hsct", "hematopoietic stem cell transplant", "bone marrow transplant",
            "allogeneic transplant", "autologous transplant",
            # Treatment terms
            "adjuvant", "neoadjuvant", "first-line", "second-line",
            "maintenance therapy", "induction therapy",
            # Common abbreviations
            "nsclc", "sclc", "crc", "hcc", "rcc", "dlbcl",
            "aml", "all", "cml", "cll", "mds",
            "tnbc", "her2+", "her2-", "hr+", "brca",
        ]

        # Check for oncology keywords
        for keyword in oncology_keywords:
            if keyword in text:
                logger.info(f"Oncology keyword detected: '{keyword}'")
                return True

        # Non-oncology indicators (negative signal)
        non_oncology_keywords = [
            # Benign hematology
            "hemophilia", "sickle cell", "thalassemia",
            "von willebrand", "itp", "thrombocytopenia",
            # Cardiology
            "heart failure", "atrial fibrillation", "hypertension",
            "coronary artery", "myocardial infarction",
            # Neurology
            "alzheimer", "parkinson", "multiple sclerosis",
            "epilepsy", "migraine", "dementia",
            # Endocrinology
            "diabetes", "thyroid", "insulin", "a1c", "hba1c",
            "metformin", "glp-1",
            # Rheumatology
            "rheumatoid arthritis", "lupus", "psoriatic arthritis",
            # Solid organ transplant (non-oncology context)
            "kidney transplant", "liver transplant", "heart transplant",
            "lung transplant", "solid organ transplant",
            # Other
            "osteoporosis", "asthma", "copd", "hepatitis",
            "congenital cmv",  # Congenital CMV is non-oncology
        ]

        # If strong non-oncology signal and no oncology keywords, return False
        for keyword in non_oncology_keywords:
            if keyword in text:
                logger.info(f"Non-oncology keyword detected: '{keyword}'")
                return False

        # Default: assume oncology if no clear signal (safer for oncology-focused pipeline)
        logger.warning("No clear oncology/non-oncology signal, defaulting to oncology=True")
        return True
