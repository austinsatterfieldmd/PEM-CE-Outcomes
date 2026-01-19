"""
Constants for disease states, abbreviations, and tag values.
Migrated from V2 - Core domain knowledge for CME question tagging.
"""

# Canonical Disease States
# Solid Tumors (common)
SOLID_TUMORS_COMMON = [
    "Breast cancer",
    "NSCLC",
    "SCLC",
    "CRC",  # Colorectal cancer
    "Prostate cancer",
    "Bladder cancer",
    "RCC",  # Renal cell carcinoma
    "Ovarian cancer",
    "Endometrial cancer",
    "Anal cancer",
    "Hepatobiliary cancer",
    "Uterine cancer",
    "Cervical cancer",
    "Melanoma",
    "Cholangiocarcinoma",
    "Pancreatic cancer",
    "Esophagogastric / GEJ cancer",
    "HCC",  # Hepatocellular carcinoma
    "Head & Neck",  # HNSCC
    "Sarcoma",
]

# Solid Tumors (less common / rare)
SOLID_TUMORS_RARE = [
    "Glioma",  # NOTE: Glioblastoma (GBM) is a disease_type under Glioma, not a disease_state
    "GIST",
    "Tenosynovial giant cell tumor",
    "Merkel cell carcinoma",
    "Mesothelioma",
    "Adrenocortical carcinoma",
    "Thyroid cancer",
    "Basal cell carcinoma",
    "Cutaneous squamous cell carcinoma",
    "EP-NECs",  # Extra-pulmonary Neuroendocrine Carcinomas
]

# Hematologic Malignancies
HEMATOLOGIC_MALIGNANCIES = [
    "Multiple Myeloma",
    "DLBCL",
    "FL",  # Follicular lymphoma
    "MCL",  # Mantle cell lymphoma
    "PTCL",  # Peripheral T-cell lymphoma
    "MZL",  # Marginal zone lymphoma
    "Burkitt lymphoma",
    "NHL",  # Non-Hodgkin lymphoma
    "CLL",  # Chronic lymphocytic leukemia
    "AML",  # Acute myeloid leukemia
    "ALL",  # Acute lymphoblastic leukemia
    "CML",  # Chronic myeloid leukemia
    "Hairy cell leukemia",
    "MDS",  # Myelodysplastic syndromes
    "Myelofibrosis",
    "Essential Thrombocythemia",
    "PV",  # Polycythemia Vera
    "BPDCN",  # Blastic Plasmacytoid Dendritic Cell Neoplasm
    "Waldenström",
    "Hodgkin lymphoma",
    "GVHD",  # Graft-versus-host disease (grouped with heme malignancies)
]

# Umbrella Tags
UMBRELLA_TAGS = [
    "Pan-tumor",
    "Heme Malignancies",
    "GI Cancers",
    "Gyn Cancers",
]

# All Disease States (for classifier)
DISEASE_STATES = (
    SOLID_TUMORS_COMMON
    + SOLID_TUMORS_RARE
    + HEMATOLOGIC_MALIGNANCIES
    + UMBRELLA_TAGS
)

# Disease State abbreviations and aliases
# Format: abbreviation/variant -> canonical name
DISEASE_ABBREVIATIONS = {
    # Breast cancer variants
    "mBC": "Breast cancer",
    "MBC": "Breast cancer",
    "mTNBC": "Breast cancer",
    "TNBC": "Breast cancer",
    "HR+/HER2-": "Breast cancer",
    "HR+/HER2−": "Breast cancer",
    "HER2+": "Breast cancer",
    "HER2-low": "Breast cancer",
    "HR+": "Breast cancer",

    # Lung cancer variants
    "NSCLC": "NSCLC",
    "non-small cell lung cancer": "NSCLC",
    "non small cell lung cancer": "NSCLC",
    "SCLC": "SCLC",
    "small cell lung cancer": "SCLC",
    "small-cel lung cancer": "SCLC",
    "LS-SCLC": "SCLC",
    "ES-SCLC": "SCLC",
    "EGFRm NSCLC": "NSCLC",
    "EGFR-mutant NSCLC": "NSCLC",

    # Colorectal cancer
    "CRC": "CRC",
    "mCRC": "CRC",  # metastatic CRC
    "colorectal cancer": "CRC",
    "colon cancer": "CRC",
    "rectal cancer": "CRC",

    # Multiple Myeloma
    "MM": "Multiple Myeloma",
    "R/R MM": "Multiple Myeloma",
    "RRMM": "Multiple Myeloma",
    "relapsed/refractory multiple myeloma": "Multiple Myeloma",
    "NDMM": "Multiple Myeloma",
    "newly diagnosed multiple myeloma": "Multiple Myeloma",

    # Prostate cancer
    "mCRPC": "Prostate cancer",
    "metastatic castration-resistant prostate cancer": "Prostate cancer",
    "HSPC": "Prostate cancer",
    "hormone-sensitive prostate cancer": "Prostate cancer",

    # Lymphomas
    "DLBCL": "DLBCL",
    "diffuse large B-cell lymphoma": "DLBCL",
    "LBCL": "DLBCL",
    "FL": "FL",
    "follicular lymphoma": "FL",
    "MCL": "MCL",
    "mantle cell lymphoma": "MCL",
    "PTCL": "PTCL",
    "peripheral T-cell lymphoma": "PTCL",
    "MZL": "MZL",
    "marginal zone lymphoma": "MZL",
    "Burkitt lymphoma": "Burkitt lymphoma",
    "burkitt's lymphoma": "Burkitt lymphoma",
    "burkitts lymphoma": "Burkitt lymphoma",
    "NHL": "NHL",
    "non-hodgkin lymphoma": "NHL",
    "non hodgkin lymphoma": "NHL",
    "non-hodgkin's lymphoma": "NHL",
    "non hodgkin's lymphoma": "NHL",
    "nonhodgkin lymphoma": "NHL",

    # Leukemias
    "AML": "AML",
    "acute myeloid leukemia": "AML",
    "ALL": "ALL",
    "acute lymphoblastic leukemia": "ALL",
    "CLL": "CLL",
    "chronic lymphocytic leukemia": "CLL",
    "CML": "CML",
    "chronic myeloid leukemia": "CML",
    "HCL": "Hairy cell leukemia",
    "hairy cell leukemia": "Hairy cell leukemia",

    # Glioma variants
    # NOTE: GBM/Glioblastoma maps to disease_state="Glioma" with disease_type="Glioblastoma"
    "GBM": "Glioma",
    "glioblastoma": "Glioma",
    "glioblastoma multiforme": "Glioma",
    "glioma": "Glioma",
    "astrocytoma": "Glioma",
    "oligodendroglioma": "Glioma",
    "low-grade glioma": "Glioma",
    "LGG": "Glioma",

    # Melanoma variants
    "uveal melanoma": "Melanoma",

    # Additional tumor types
    "RCC": "RCC",
    "renal cell carcinoma": "RCC",
    "HCC": "HCC",
    "hepatocellular carcinoma": "HCC",
    "HNSCC": "Head & Neck",
    "head and neck": "Head & Neck",
    "head & neck": "Head & Neck",

    # Hodgkin lymphoma variants
    "cHL": "Hodgkin lymphoma",
    "HL": "Hodgkin lymphoma",
    "hodgkin lymphoma": "Hodgkin lymphoma",
    "hodgkin's lymphoma": "Hodgkin lymphoma",
    "hodgkins lymphoma": "Hodgkin lymphoma",
    "classical hodgkin lymphoma": "Hodgkin lymphoma",

    # Urothelial cancer variants
    "urothelial carcinoma": "Urothelial cancer",
    "urothelial cancer": "Urothelial cancer",
    "bladder carcinoma": "Urothelial cancer",
    "transitional cell carcinoma": "Urothelial cancer",
    "TCC": "Urothelial cancer",

    # Uterine cancer variants
    "uterine cancer": "Uterine cancer",
    "uterine carcinoma": "Uterine cancer",

    # Ovarian cancer variants
    "PROC": "Ovarian cancer",  # Platinum-resistant ovarian cancer
    "platinum-resistant ovarian cancer": "Ovarian cancer",
    "platinum resistant ovarian cancer": "Ovarian cancer",

    # Gastric/Esophagogastric cancer variants
    "gastric cancer": "Esophagogastric / GEJ cancer",
    "gastric adenocarcinoma": "Esophagogastric / GEJ cancer",
    "GEJ": "Esophagogastric / GEJ cancer",
    "gastroesophageal junction": "Esophagogastric / GEJ cancer",
    "GEJ cancer": "Esophagogastric / GEJ cancer",

    # Myeloproliferative neoplasms
    "PV": "PV",
    "polycythemia vera": "PV",
    "polycythemia": "PV",

    # Rare hematologic malignancies
    "BPDCN": "BPDCN",
    "blastic plasmacytoid dendritic cell neoplasm": "BPDCN",

    # Skin cancers
    "BCC": "Basal cell carcinoma",
    "basal cell carcinoma": "Basal cell carcinoma",
    "cSCC": "Cutaneous squamous cell carcinoma",
    "cutaneous squamous cell carcinoma": "Cutaneous squamous cell carcinoma",
    "cutaneous SCC": "Cutaneous squamous cell carcinoma",

    # Neuroendocrine tumors
    "EP-NECs": "EP-NECs",
    "EP-NEC": "EP-NECs",
    "extra-pulmonary neuroendocrine carcinoma": "EP-NECs",
    "extra-pulmonary NEC": "EP-NECs",
    "extrapulmonary neuroendocrine carcinoma": "EP-NECs",
}

# Disease subtype mappings
# Maps disease subtypes/histological types to canonical disease states
DISEASE_SUBTYPES = {
    # Breast cancer subtypes
    "invasive ductal carcinoma": "Breast cancer",
    "IDC": "Breast cancer",
    "invasive lobular carcinoma": "Breast cancer",
    "ILC": "Breast cancer",
    "ductal carcinoma": "Breast cancer",
    "lobular carcinoma": "Breast cancer",
    "triple negative breast cancer": "Breast cancer",
    "TNBC": "Breast cancer",
    "triple-negative breast cancer": "Breast cancer",
    "ER+/HER2-": "Breast cancer",
    "ER+/HER2−": "Breast cancer",
    "HR+/HER2-": "Breast cancer",
    "HR+/HER2−": "Breast cancer",
    "HER2+": "Breast cancer",
    "HER2-positive": "Breast cancer",
    "HER2-low": "Breast cancer",
    "HER2-low breast cancer": "Breast cancer",

    # Urothelial cancer subtypes
    "urothelial carcinoma": "Urothelial cancer",
    "urothelial cancer": "Urothelial cancer",
    "bladder carcinoma": "Urothelial cancer",
    "transitional cell carcinoma": "Urothelial cancer",
    "TCC": "Urothelial cancer",

    # Lung cancer subtypes
    "adenocarcinoma": None,  # Context-dependent
    "squamous cell carcinoma": None,  # Context-dependent
    "large cell carcinoma": "NSCLC",

    # Other common subtypes
    "clear cell carcinoma": None,  # Context-dependent (RCC, ovarian, etc.)
    "serous carcinoma": None,  # Could be ovarian, endometrial
    "uterine serous carcinoma": "Uterine cancer",
    "gastric adenocarcinoma": "Esophagogastric / GEJ cancer",
    "cutaneous squamous cell carcinoma": "Cutaneous squamous cell carcinoma",
    "basal cell carcinoma": "Basal cell carcinoma",
}

# GVHD Detection Keywords
GVHD_KEYWORDS = [
    "gvhd",
    "graft-versus-host",
    "graft versus host",
    "allo-hct",
    "allogeneic transplant",
    "allogeneic hematopoietic cell transplantation",
    "post-transplant",
    "post transplant",
    "acute gvhd",
    "chronic gvhd",
    "aGVHD",
    "cGVHD",
]

# GVHD Context Keywords (symptoms/indicators)
GVHD_CONTEXT_KEYWORDS = [
    "diarrhea",
    "rash",
    "liver dysfunction",
    "biopsy",
    "steroid-refractory",
    "steroid refractory",
]

# Activity Name to Disease State Mappings
# Used as priors when activity metadata is available
ACTIVITY_DISEASE_MAPPINGS = {
    # Breast cancer activities
    "breast": "Breast cancer",
    "breast cancer": "Breast cancer",
    "mammary": "Breast cancer",

    # Lung cancer activities
    "lung": "NSCLC",  # Default to NSCLC unless specified SCLC
    "nsclc": "NSCLC",
    "sclc": "SCLC",
    "thoracic": "NSCLC",

    # Colorectal cancer activities
    "crc": "CRC",
    "colorectal": "CRC",
    "colon": "CRC",
    "rectal": "CRC",
    "gi cancers": "CRC",
    "gastrointestinal": "CRC",

    # Hematologic malignancies
    "heme": "Heme Malignancies",
    "hematologic": "Heme Malignancies",
    "hematological": "Heme Malignancies",
    "lymphoma": "DLBCL",  # Default
    "leukemia": "AML",  # Default
    "myeloma": "Multiple Myeloma",

    # Other
    "prostate": "Prostate cancer",
    "ovarian": "Ovarian cancer",
    "melanoma": "Melanoma",
    "sarcoma": "Sarcoma",
}

# Pan-tumor indicators (explicit phrases that suggest pan-tumor)
PAN_TUMOR_INDICATORS = [
    "solid tumors",
    "solid tumor",
    "solid malignancies",
    "ntrk fusion",
    "ntrk-fusion",
    "msi-h solid tumors",
    "msi-high solid tumors",
    "tumor-agnostic",
    "tumor agnostic",
    "pan-tumor",
    "pan tumor",
    "across tumor types",
    "multiple tumor types",
]

# Tag Priority Order
TAG_PRIORITY = {
    "Disease State": 1,  # Highest priority
    "Topic": 2,
    "Treatment": 3,
    "Disease Stage": 4,
    "Disease Type": 5,
    "Treatment Line": 6,
    "Biomarker": 7,
    "Trial": 8,
}

# Valid Disease Stages by Disease Category
VALID_DISEASE_STAGES = {
    "solid_tumor": ["Early-stage", "Early-stage resectable", "Early-stage unresectable", "Metastatic"],
    "sclc": ["Limited-stage", "Extensive-stage"],
    "hematologic": None,  # No staging for hematologic malignancies
}

# Valid Treatment Lines by Stage
VALID_TREATMENT_LINES = {
    "early_stage": ["Adjuvant", "Neoadjuvant", "Perioperative"],
    "metastatic": ["1L", "2L+"],
    "hematologic": ["Newly diagnosed", "R/R", "Maintenance", "Bridging"],
    "gvhd": ["Steroid-naive", "Steroid-refractory", "Prophylaxis"],
}
