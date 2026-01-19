"""
Disease Classifier - Stage 1 of two-stage tagging architecture.

This module provides combined oncology gate + disease state classification from clinical questions.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Union

logger = logging.getLogger(__name__)


class DiseaseClassifier:
    """
    Stage 1: Combined oncology gate + disease state detection.

    Performs two classifications:
    1. is_oncology: Is this an oncology/hematologic malignancy question?
    2. disease_state: If oncology, what is the primary cancer type?

    Uses a single premium LLM with optional web search fallback for
    trial-based inference.
    """

    def __init__(self, client, model: str = "claude"):
        """
        Initialize the disease classifier.

        Args:
            client: OpenRouterClient instance for LLM calls
            model: Model to use for classification ("claude", "gpt", or "gemini")
        """
        self.client = client
        self.model = model
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
        activity_name: Optional[str] = None
    ) -> Dict[str, Union[bool, Optional[str]]]:
        """
        Classify oncology status and disease state from a question.

        Args:
            question_text: The question text
            correct_answer: The correct answer text (optional but recommended)
            activity_name: The activity/course title (optional, provides context)

        Returns:
            {
                "is_oncology": True/False,
                "disease_state": "Breast cancer"  # or null if non-oncology or not determined
            }
        """
        # Build prompt with question context
        messages = self._build_messages(question_text, correct_answer, activity_name)

        # Call LLM for initial classification
        logger.info(f"Classifying oncology status and disease state using {self.model}")
        result = await self._call_llm(messages)

        # Ensure is_oncology field exists (fallback to keyword detection)
        if "is_oncology" not in result:
            logger.warning("Response missing is_oncology, using keyword fallback")
            result["is_oncology"] = self._detect_oncology_keywords(
                question_text, correct_answer or ""
            )

        # If not oncology, disease_state must be null
        if not result.get("is_oncology"):
            result["disease_state"] = None
            logger.info("Question classified as non-oncology")
            return result

        # For oncology questions: if disease_state is null, try web search for trial names
        if not result.get("disease_state"):
            logger.info("Oncology question but disease state not determined, checking for trial names")
            trial_name = self._extract_trial_name(question_text)

            if trial_name:
                logger.info(f"Found trial name: {trial_name}, attempting web search")
                search_result = await self._search_trial_disease(trial_name)

                if search_result:
                    logger.info(f"Web search identified disease: {search_result}")
                    result["disease_state"] = search_result
                else:
                    logger.warning(f"Web search failed to identify disease for trial {trial_name}")

        return result

    def _build_messages(
        self,
        question_text: str,
        correct_answer: Optional[str] = None,
        activity_name: Optional[str] = None
    ) -> list:
        """Build messages for LLM call."""
        messages = [
            {"role": "system", "content": self.prompt}
        ]

        # Build user message with all available context
        user_content = f"Question: {question_text}\n"

        if correct_answer:
            user_content += f"Correct Answer: {correct_answer}\n"

        if activity_name:
            user_content += f"Activity Name: {activity_name}\n"

        messages.append({"role": "user", "content": user_content})

        return messages

    async def _call_llm(self, messages: list) -> Dict[str, Optional[str]]:
        """Call LLM and parse response."""
        try:
            # Use the client's generate method for single model
            response = await self.client.generate(
                messages=messages,
                model=self.model,
                temperature=0.0  # Deterministic classification
            )

            # Parse JSON from response
            content = response.get("content", "")
            parsed = self._parse_json_response(content)

            return parsed

        except Exception as e:
            logger.error(f"Error calling LLM for disease classification: {e}")
            return {"disease_state": None}

    def _parse_json_response(self, content: str) -> Dict[str, Union[bool, Optional[str]]]:
        """
        Parse JSON response from LLM.

        Handles responses with or without markdown code blocks.

        Returns:
            {
                "is_oncology": True/False (may be missing, caller should use fallback)
                "disease_state": str or None
            }
        """
        # Remove markdown code blocks if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        elif content.startswith("```"):
            content = content[3:]  # Remove ```

        if content.endswith("```"):
            content = content[:-3]  # Remove closing ```

        content = content.strip()

        try:
            parsed = json.loads(content)

            result = {}

            # Extract is_oncology if present
            if "is_oncology" in parsed:
                result["is_oncology"] = bool(parsed["is_oncology"])

            # Extract disease_state
            result["disease_state"] = parsed.get("disease_state")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Content: {content}")
            return {"disease_state": None}

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
            disease = self._parse_disease_from_search(search_result, trial_name)

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
            "Melanoma", "Head & Neck", "HCC", "Pancreatic cancer",
            "Cholangiocarcinoma", "Esophagogastric cancer", "Cervical cancer",
            "Uterine cancer", "Sarcoma", "Multiple Myeloma", "DLBCL", "FL",
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
            "multiple myeloma": "Multiple Myeloma",
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

        Used when LLM response doesn't include is_oncology field.

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
