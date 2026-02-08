"""
Multi-Model Tagger for V3 3-Model LLM Voting System.

Orchestrates the tagging workflow:
V1 (Single-stage):
1. Load question and enrich with KB context
2. Call 3 models in parallel (GPT, Claude, Gemini)
3. Aggregate votes and determine agreement
4. Optionally trigger web search for unknown entities
5. Store results for review

V2 (Two-stage):
1. Stage 1: Disease classification (single model, lightweight)
2. Stage 2: Disease-specific tagging (3 models, parallel voting)
3. Aggregate votes and determine agreement
4. Optionally trigger web search for unknown entities
5. Store results for review
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from .openrouter_client import OpenRouterClient, get_openrouter_client
from .vote_aggregator import VoteAggregator, AggregatedVote, AgreementLevel
from .disease_classifier import DiseaseClassifier
from ..services.prompt_manager import PromptManager, get_prompt_manager

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"


class MultiModelTagger:
    """
    Orchestrates 3-model LLM voting for question tagging.

    Usage:
        tagger = MultiModelTagger()
        result = await tagger.tag_question(question_id, question_text)
    """

    def __init__(
        self,
        client: Optional[OpenRouterClient] = None,
        prompt_version: str = "v2.0",
        use_web_search: bool = True,
        web_search_threshold: float = 0.5,
        disease_classifier_model: str = "claude"
    ):
        """
        Initialize multi-model tagger.

        Args:
            client: OpenRouter client instance (creates default if None)
            prompt_version: Version of prompt to use ("v1.0" or "v2.0")
            use_web_search: Whether to enable web search for unknown entities
            web_search_threshold: Confidence threshold below which to trigger web search
            disease_classifier_model: Model to use for Stage 1 classification (v2.0 only)
        """
        self.client = client or get_openrouter_client()
        self.aggregator = VoteAggregator()
        self.prompt_version = prompt_version
        self.use_web_search = use_web_search
        self.web_search_threshold = web_search_threshold

        # Determine if using two-stage (v2.0) or single-stage (v1.0)
        self.use_two_stage = prompt_version == "v2.0"

        if self.use_two_stage:
            # V2.0: Two-stage approach
            self.disease_classifier = DiseaseClassifier(
                client=self.client,
                use_voting=True
            )
            self.prompt_manager = get_prompt_manager()
            logger.info("Initialized two-stage tagger (v2.0) with 2-model voting")
        else:
            # V1.0: Single-stage approach (legacy)
            self.system_prompt = self._load_prompt("system_prompt.txt")
            self.few_shot_examples = self._load_json("few_shot_examples.json")
            logger.info("Initialized single-stage tagger (v1.0)")

    def _load_prompt(self, filename: str) -> str:
        """Load a prompt template file."""
        prompt_path = PROMPTS_DIR / self.prompt_version / filename
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            logger.warning(f"Prompt file not found: {prompt_path}. Using default.")
            return self._get_default_system_prompt()

    def _load_json(self, filename: str) -> List[Dict]:
        """Load a JSON file from prompts directory."""
        json_path = PROMPTS_DIR / self.prompt_version / filename
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _get_default_system_prompt(self) -> str:
        """Return default system prompt if file not found."""
        return """You are an expert medical education analyst specializing in oncology CME (Continuing Medical Education) content.

Your task is to tag clinical questions with the following categories:

1. **topic**: The educational topic (one of: Treatment selection, Clinical efficacy, Safety profile, AE management, Disease overview, Diagnostic workup, Emerging therapies, Guidelines/evidence, Patient communication, Biomarker testing)

2. **disease_state**: The specific cancer type (e.g., "NSCLC", "Breast cancer", "CML", "Multiple myeloma")

3. **disease_stage**: The stage of disease if mentioned (e.g., "Early stage", "Metastatic", "Locally advanced", "Relapsed/refractory")

4. **disease_type**: Specific subtype if applicable (e.g., "HER2+", "Triple-negative", "ALK+", "EGFR-mutated")

5. **treatment_line**: Line of therapy (e.g., "First-line", "Second-line", "Maintenance", "Adjuvant", "Neoadjuvant")

6. **treatment**: Specific treatment mentioned (drug names, regimens, or treatment modalities)

7. **biomarker**: Relevant biomarkers (e.g., "PD-L1", "BRCA1/2", "HER2", "EGFR", "ALK")

8. **trial**: Clinical trial name if mentioned (e.g., "KEYNOTE-024", "CheckMate-227", "DESTINY-Breast03")

Respond with a JSON object containing only these 8 fields. Use null for fields that are not applicable or cannot be determined from the question.

Example response format:
{
    "topic": "Treatment selection",
    "disease_state": "NSCLC",
    "disease_stage": "Metastatic",
    "disease_type": "EGFR-mutated",
    "treatment_line": "First-line",
    "treatment": "osimertinib",
    "biomarker": "EGFR",
    "trial": null
}"""

    def _build_messages(
        self,
        question_text: str,
        correct_answer: Optional[str] = None,
        incorrect_answers: Optional[List[str]] = None,
        kb_context: Optional[Dict] = None,
        disease_prompt: Optional[str] = None,
        known_disease_state: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Build message list for LLM call.

        Args:
            question_text: The question text
            correct_answer: Optional correct answer
            incorrect_answers: Optional list of incorrect answer options
            kb_context: Optional knowledge base context
            disease_prompt: Disease-specific prompt (v2.0 only)
            known_disease_state: Known disease state from Stage 1 (v2.0 only)

        Returns:
            List of message dicts
        """
        messages = []

        # System message
        if disease_prompt:
            # V2.0: Disease-specific prompt
            messages.append({"role": "system", "content": disease_prompt})
        else:
            # V1.0: Generic prompt
            messages.append({"role": "system", "content": self.system_prompt})

            # Add few-shot examples for V1.0
            for example in self.few_shot_examples[:3]:  # Limit to 3 examples
                messages.append({
                    "role": "user",
                    "content": f"Question: {example.get('question', '')}"
                })
                messages.append({
                    "role": "assistant",
                    "content": json.dumps(example.get("tags", {}), indent=2)
                })

        # User message with question
        user_content = f"Question: {question_text}\n"
        if correct_answer:
            user_content += f"\nCorrect Answer: {correct_answer}\n"

        # Add answer options if provided
        if incorrect_answers:
            user_content += "\nIncorrect Answer Options:\n"
            for i, ans in enumerate(incorrect_answers, 1):
                user_content += f"  {i}. {ans}\n"

            # Add guidance for using answer options
            user_content += """
IMPORTANT - Answer Options Usage:
- If the correct answer is a compound answer (e.g., "A and B", "All of the above"),
  extract ALL relevant entities from the combined answer options for tagging.
  Example: If correct answer is "A and B" where A=trastuzumab and B=pertuzumab,
  tag BOTH in treatment_1 and treatment_2.
- Use the answer options to evaluate question quality fields (Group F):
  answer_format, distractor_homogeneity, and flaw_* fields.
- Consider what the answer options reveal about the educational focus.
"""

        # V2.0: Inject known disease info from Stage 1
        if known_disease_state:
            user_content += f"\nContext: This question is about {known_disease_state}.\n"

        if kb_context:
            user_content += f"\nKnowledge Base Context: {json.dumps(kb_context)}\n"

        messages.append({"role": "user", "content": user_content})

        return messages

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response to extract tags."""
        try:
            # Try to find JSON in the response
            content = content.strip()

            # Handle markdown code blocks
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return {}

    async def _call_models_parallel(
        self,
        messages: List[Dict[str, str]]
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """Call all 3 models in parallel."""
        responses = await self.client.generate_parallel(
            messages=messages,
            models=["gpt", "claude", "gemini"],
            response_format={"type": "json_object"}
        )

        # Parse responses
        gpt_tags = self._parse_response(responses.get("gpt", {}).get("content", ""))
        claude_tags = self._parse_response(responses.get("claude", {}).get("content", ""))
        gemini_tags = self._parse_response(responses.get("gemini", {}).get("content", ""))

        return gpt_tags, claude_tags, gemini_tags

    async def _perform_web_search(
        self,
        question_text: str,
        unknown_entities: List[str],
        field_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform web search for unknown entities in Stage 2.

        Different from Stage 1 web search which only looks up disease from trials.
        Stage 2 web search resolves conflicts in factual tag fields.

        Args:
            question_text: The question text
            unknown_entities: List of entities to search
            field_type: Type of field (treatment, trial, biomarker, etc.)

        Returns:
            List of search results
        """
        searches = []

        for entity in unknown_entities[:3]:  # Limit to 3 searches
            try:
                # Build field-specific query and context
                if field_type == "trial":
                    query = f"{entity} oncology clinical trial results efficacy"
                    context = f"What are the key findings and disease studied in the {entity} trial?"
                elif field_type == "treatment":
                    query = f"{entity} oncology FDA approval indications mechanism"
                    context = f"What are the FDA-approved indications and mechanism of action for {entity}?"
                elif field_type == "biomarker":
                    query = f"{entity} biomarker cancer predictive prognostic testing"
                    context = f"What is {entity} as a biomarker in oncology? Predictive or prognostic?"
                elif field_type == "disease_stage":
                    query = f"{entity} cancer staging definition"
                    context = f"What does '{entity}' mean in cancer staging?"
                elif field_type == "disease_type":
                    query = f"{entity} cancer subtype classification"
                    context = f"What is {entity} as a cancer subtype?"
                elif field_type == "treatment_line":
                    query = f"{entity} treatment line oncology definition"
                    context = f"What does '{entity}' mean in oncology treatment lines?"
                else:
                    # Generic fallback
                    query = f"oncology clinical trial treatment {entity}"
                    context = f"Looking up information about '{entity}' mentioned in a medical education question."

                result = await self.client.web_search(
                    query=query,
                    context=context
                )
                searches.append({
                    "entity": entity,
                    "field_type": field_type,
                    "query": query,
                    "result": result.get("content", "")[:500]  # Truncate
                })
            except Exception as e:
                logger.warning(f"Web search failed for '{entity}': {e}")

        return searches

    async def tag_question(
        self,
        question_id: int,
        question_text: str,
        correct_answer: Optional[str] = None,
        incorrect_answers: Optional[List[str]] = None,
        kb_context: Optional[Dict] = None,
        known_disease_state: Optional[str] = None
    ) -> AggregatedVote:
        """
        Tag a single question with 3-model voting.

        For v2.0 (two-stage):
            1. Stage 1: Classify disease state (single model) - SKIPPED if known_disease_state provided
            2. Stage 2: Disease-specific tagging (3 models)

        For v1.0 (single-stage):
            1. Tag with 3 models in parallel (legacy)

        Args:
            question_id: Database ID of the question
            question_text: The question stem text
            correct_answer: Optional correct answer text
            incorrect_answers: Optional list of incorrect answer options (needed for compound
                             answer analysis and question quality assessment)
            kb_context: Optional knowledge base context
            known_disease_state: If provided, skip Stage 1 and use this disease state directly.
                               This is used when re-running Stage 2 for questions with known disease.

        Returns:
            AggregatedVote with voting results
        """
        logger.info(f"Tagging question {question_id} (version: {self.prompt_version})")

        if self.use_two_stage:
            # === V2.0: TWO-STAGE FLOW ===
            return await self._tag_question_two_stage(
                question_id, question_text, correct_answer, incorrect_answers, kb_context,
                known_disease_state=known_disease_state
            )
        else:
            # === V1.0: SINGLE-STAGE FLOW ===
            return await self._tag_question_single_stage(
                question_id, question_text, correct_answer, kb_context
            )

    async def _tag_question_single_stage(
        self,
        question_id: int,
        question_text: str,
        correct_answer: Optional[str] = None,
        kb_context: Optional[Dict] = None
    ) -> AggregatedVote:
        """V1.0: Single-stage tagging (legacy)."""
        # Build messages with generic prompt
        messages = self._build_messages(
            question_text=question_text,
            correct_answer=correct_answer,
            kb_context=kb_context
        )

        # Call models in parallel
        gpt_tags, claude_tags, gemini_tags = await self._call_models_parallel(messages)

        # Aggregate votes
        aggregated = self.aggregator.aggregate(
            question_id=question_id,
            gpt_response=gpt_tags,
            claude_response=claude_tags,
            gemini_response=gemini_tags
        )

        # Web search for ANY disagreement (majority or conflict) - not just conflict
        if self.use_web_search and aggregated.overall_agreement in [AgreementLevel.CONFLICT, AgreementLevel.MAJORITY]:
            logger.info(f"Question {question_id}: Triggering web search due to {aggregated.overall_agreement.value} agreement")
            await self._handle_web_search(question_text, aggregated)

        logger.info(
            f"Question {question_id}: {aggregated.overall_agreement.value} "
            f"(confidence: {aggregated.overall_confidence}, needs_review: {aggregated.needs_review})"
        )

        return aggregated

    async def _tag_question_two_stage(
        self,
        question_id: int,
        question_text: str,
        correct_answer: Optional[str] = None,
        incorrect_answers: Optional[List[str]] = None,
        kb_context: Optional[Dict] = None,
        known_disease_state: Optional[str] = None
    ) -> AggregatedVote:
        """
        V2.0: Two-stage tagging with oncology gate + disease classification.

        Stage 1: Classify is_oncology and disease_state - SKIPPED if known_disease_state provided
        Stage 2: If oncology, perform disease-specific 3-model tagging
                 If non-oncology, skip Stage 2 and return minimal result

        Args:
            known_disease_state: If provided, skip Stage 1 classification entirely and use this
                               disease state. This prevents re-classification of questions that
                               already have an assigned disease state from prior Stage 1 runs.
        """
        # === STAGE 1: Oncology Gate + Disease Classification ===
        # SKIP Stage 1 if disease state is already known (e.g., from batch input file)
        if known_disease_state:
            logger.info(f"Stage 1: SKIPPED - using known disease state: {known_disease_state}")
            is_oncology = True  # If disease state is known, it's oncology
            disease_state = known_disease_state
        else:
            logger.info(f"Stage 1: Classifying oncology status and disease state for question {question_id}")
            disease_info = await self.disease_classifier.classify(
                question_text,
                correct_answer
            )
            is_oncology = disease_info.get("is_oncology", True)  # Default to True for safety
            disease_state = disease_info.get("disease_state")
            logger.info(f"Stage 1 result: is_oncology={is_oncology}, disease_state={disease_state}")

        # === NON-ONCOLOGY HANDLING ===
        # Skip Stage 2 for non-oncology questions (save $0.08)
        if not is_oncology:
            logger.info(f"Question {question_id}: Non-oncology question, skipping Stage 2")
            # Return minimal result with oncology flag for future pipeline
            return AggregatedVote(
                question_id=question_id,
                overall_agreement=AgreementLevel.UNANIMOUS,  # No conflict since not tagged
                overall_confidence=1.0,
                needs_review=False,
                final_tags={
                    "is_oncology": False,
                    "disease_state": None,
                    "topic": None,
                    "disease_stage": None,
                    "disease_type": None,
                    "treatment_line": None,
                    "treatment": None,
                    "biomarker": None,
                    "trial": None,
                    "_classification_only": True,  # Flag indicating Stage 2 was skipped
                    "_needs_non_onc_tagging": True  # Flag for future non-oncology pipeline
                }
            )

        # === STAGE 2: Disease-Specific Tagging (oncology only) ===
        logger.info(f"Stage 2: Loading disease-specific prompt for {disease_state}")

        # Load disease-specific prompt WITH few-shot examples from human corrections
        if disease_state:
            # Try to get prompt with human-corrected few-shot examples
            disease_prompt = self.prompt_manager.get_disease_prompt_with_fewshots(
                disease_state, version=self.prompt_version, num_fewshots=3
            )
            if not disease_prompt:
                logger.warning(f"No disease-specific prompt for {disease_state}, using fallback")
                disease_prompt = self.prompt_manager.get_fallback_prompt(version=self.prompt_version)
        else:
            logger.info("Disease state is null, using fallback prompt")
            disease_prompt = self.prompt_manager.get_fallback_prompt(version=self.prompt_version)

        # Build messages with disease-specific context
        messages = self._build_messages(
            question_text=question_text,
            correct_answer=correct_answer,
            incorrect_answers=incorrect_answers,
            kb_context=kb_context,
            disease_prompt=disease_prompt,
            known_disease_state=disease_state
        )

        # Call 3 models in parallel
        gpt_tags, claude_tags, gemini_tags = await self._call_models_parallel(messages)

        # Inject Stage 1 result (ensure disease_state and is_oncology are present)
        for tags in [gpt_tags, claude_tags, gemini_tags]:
            if tags:  # Guard against None
                tags["is_oncology"] = True  # All oncology at this point
                if disease_state and not tags.get("disease_state"):
                    tags["disease_state"] = disease_state

        # Aggregate votes - with error handling to preserve partial responses
        try:
            aggregated = self.aggregator.aggregate(
                question_id=question_id,
                gpt_response=gpt_tags or {},
                claude_response=claude_tags or {},
                gemini_response=gemini_tags or {}
            )
        except Exception as e:
            # Aggregation failed - create error result with partial model responses
            logger.error(f"Question {question_id}: Aggregation error - {e}")
            # Store partial responses for review
            aggregated = AggregatedVote(
                question_id=question_id,
                overall_agreement=AgreementLevel.CONFLICT,
                overall_confidence=0.0,
                needs_review=True,
                review_reason=f"api_error:{str(e)[:100]}",
                final_tags={
                    "is_oncology": True,
                    "disease_state": disease_state,
                    "_api_error": True,
                    "_error_message": str(e)
                },
                gpt_tags=gpt_tags,
                claude_tags=claude_tags,
                gemini_tags=gemini_tags
            )

        # Ensure is_oncology is in final tags
        if aggregated.final_tags:
            aggregated.final_tags["is_oncology"] = True

        # Web search for ANY disagreement (majority or conflict) - not just conflict
        if self.use_web_search and aggregated.overall_agreement in [AgreementLevel.CONFLICT, AgreementLevel.MAJORITY]:
            logger.info(f"Question {question_id}: Triggering web search due to {aggregated.overall_agreement.value} agreement")
            await self._handle_web_search(question_text, aggregated)

        logger.info(
            f"Question {question_id}: {aggregated.overall_agreement.value} "
            f"(confidence: {aggregated.overall_confidence}, needs_review: {aggregated.needs_review})"
        )

        return aggregated

    async def _handle_web_search(
        self,
        question_text: str,
        aggregated: AggregatedVote
    ):
        """
        Handle Stage 2 web search for conflicts in factual tag fields.

        This is DIFFERENT from Stage 1 web search:
        - Stage 1: Disease classification from trial names (in DiseaseClassifier)
        - Stage 2: Resolving conflicts in ALL factual tag fields (this method)

        Web search can help resolve conflicts about:
        - treatment: Drug names, regimens
        - trial: Clinical trial names and details
        - biomarker: Biomarker names and definitions
        - disease_stage: Stage definitions (e.g., "extensive-stage vs metastatic")
        - disease_type: Subtype clarification (e.g., "HER2-low vs HER2+")
        - treatment_line: Treatment line terminology (e.g., "perioperative vs neoadjuvant")

        Note: 'topic' is excluded as it requires clinical judgment, not factual lookup.
        """
        # Identify entities that might need lookup, grouped by field type
        disagreements = self.aggregator.get_disagreements(aggregated)

        # Fields that can benefit from web search (all except 'topic')
        searchable_fields = [
            "treatment",
            "trial",
            "biomarker",
            "disease_stage",
            "disease_type",
            "treatment_line"
        ]

        # Group entities by field type for more targeted searches
        entities_by_field = {}
        for d in disagreements:
            if d["field"] in searchable_fields:
                field_type = d["field"]
                if field_type not in entities_by_field:
                    entities_by_field[field_type] = []

                for val in [d["gpt"], d["claude"], d["gemini"]]:
                    if val and val not in entities_by_field[field_type]:
                        entities_by_field[field_type].append(val)

        # Perform field-specific searches
        all_searches = []
        for field_type, entities in entities_by_field.items():
            if entities:
                logger.info(f"Performing web search for {field_type}: {entities}")
                searches = await self._perform_web_search(
                    question_text,
                    entities,
                    field_type=field_type
                )
                all_searches.extend(searches)

        if all_searches:
            aggregated.web_searches_used = all_searches
            # Update review_reason to indicate web search was used
            if aggregated.review_reason:
                aggregated.review_reason = f"{aggregated.review_reason}|web_search_used"
            else:
                aggregated.review_reason = "web_search_used"
            logger.info(f"Stage 2: Completed {len(all_searches)} web searches for {aggregated.overall_agreement.value} resolution")

    async def tag_batch(
        self,
        questions: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> List[AggregatedVote]:
        """
        Tag a batch of questions.

        Args:
            questions: List of question dicts with 'id', 'question_stem', 'correct_answer'
            progress_callback: Optional callback(completed, total) for progress updates

        Returns:
            List of AggregatedVote results
        """
        results = []
        total = len(questions)

        for i, q in enumerate(questions):
            try:
                result = await self.tag_question(
                    question_id=q["id"],
                    question_text=q["question_stem"],
                    correct_answer=q.get("correct_answer")
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error tagging question {q['id']}: {e}")
                # Create error result
                results.append(AggregatedVote(
                    question_id=q["id"],
                    overall_agreement=AgreementLevel.CONFLICT,
                    overall_confidence=0.0,
                    needs_review=True
                ))

            if progress_callback:
                progress_callback(i + 1, total)

        return results

    def get_stats(self, results: List[AggregatedVote]) -> Dict[str, Any]:
        """
        Get statistics for a batch of tagging results.

        Args:
            results: List of AggregatedVote results

        Returns:
            Dict with statistics
        """
        stats = {
            "total": len(results),
            "unanimous": 0,
            "majority": 0,
            "conflict": 0,
            "needs_review": 0,
            "api_cost": self.client.get_total_cost()
        }

        for r in results:
            if r.overall_agreement == AgreementLevel.UNANIMOUS:
                stats["unanimous"] += 1
            elif r.overall_agreement == AgreementLevel.MAJORITY:
                stats["majority"] += 1
            else:
                stats["conflict"] += 1

            if r.needs_review:
                stats["needs_review"] += 1

        return stats


# Singleton instance
_tagger_instance: Optional[MultiModelTagger] = None


def get_multi_model_tagger() -> MultiModelTagger:
    """Get or create multi-model tagger singleton."""
    global _tagger_instance
    if _tagger_instance is None:
        _tagger_instance = MultiModelTagger()
    return _tagger_instance
