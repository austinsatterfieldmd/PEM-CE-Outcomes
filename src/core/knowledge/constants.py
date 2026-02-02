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
    "Hepatobiliary cancer",  # Includes Cholangiocarcinoma, Gallbladder carcinoma as disease_type
    "Uterine cancer",
    "Cervical cancer",
    "Melanoma",
    "Pancreatic cancer",
    "Esophagogastric / GEJ cancer",
    "HCC",  # Hepatocellular carcinoma
    "Head & neck",  # HNSCC
    "Sarcoma",  # Includes GIST as disease_type
]

# Solid Tumors (less common / rare)
SOLID_TUMORS_RARE = [
    "Glioma",  # NOTE: Glioblastoma (GBM) is a disease_type under Glioma, not a disease_state
    # NOTE: GIST is now a disease_type under Sarcoma, not a standalone disease_state
    "Tenosynovial giant cell tumor",
    "Merkel cell carcinoma",
    "Mesothelioma",
    "Adrenocortical carcinoma",
    "Thyroid cancer",
    "Basal cell carcinoma",
    "Cutaneous squamous cell carcinoma",
    "EP-NEC",  # Extra-pulmonary Neuroendocrine Carcinoma (singular)
    "GEP-NET",  # Gastroenteropancreatic Neuroendocrine Tumor (singular)
    "LCNEC",  # Large cell neuroendocrine carcinoma
    "NF1-associated plexiform neurofibroma",  # Neurofibromatosis type 1 tumors
    "Desmoid tumor",
    "Testicular cancer",
    "Thymic cancer",  # Includes thymoma
]

# Paraneoplastic/Cancer-Associated Syndromes
PARANEOPLASTIC_SYNDROMES = [
    "LEMS",  # Lambert-Eaton Myasthenic Syndrome - often associated with SCLC
]

# Hematologic Malignancies
HEMATOLOGIC_MALIGNANCIES = [
    "Multiple myeloma",
    "DLBCL",
    "FL",  # Follicular lymphoma
    "MCL",  # Mantle cell lymphoma
    "PTCL",  # Peripheral T-cell lymphoma
    "CTCL",  # Cutaneous T-cell lymphoma
    "MZL",  # Marginal zone lymphoma
    "Burkitt lymphoma",
    "NHL",  # Non-Hodgkin lymphoma
    "CLL",  # Chronic lymphocytic leukemia
    "AML",  # Acute myeloid leukemia
    "ALL",  # Acute lymphoblastic leukemia
    "CML",  # Chronic myeloid leukemia
    "CMML",  # Chronic myelomonocytic leukemia
    "Hairy cell leukemia",
    "MDS",  # Myelodysplastic syndromes
    "MPN",  # Myeloproliferative neoplasms (umbrella for MF, ET, PV)
    "MF",
    "ET",
    "PV",  # Polycythemia Vera
    "BPDCN",  # Blastic Plasmacytoid Dendritic Cell Neoplasm
    "Waldenström",
    "Hodgkin lymphoma",
    "GVHD",  # Graft-versus-host disease (grouped with heme malignancies)
    "CMV",  # Cytomegalovirus in BMT/HSCT context (oncology)
]

# Umbrella Tags
UMBRELLA_TAGS = [
    "Pan-tumor",
    "Heme malignancies",
    "GI cancers",
    "Gyn cancers",
]

# All Disease States (for classifier)
DISEASE_STATES = (
    SOLID_TUMORS_COMMON
    + SOLID_TUMORS_RARE
    + HEMATOLOGIC_MALIGNANCIES
    + PARANEOPLASTIC_SYNDROMES
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
    "BIA-ALCL": "Breast cancer",  # Breast implant-associated ALCL - managed by breast specialists
    "breast implant-associated ALCL": "Breast cancer",

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

    # Multiple myeloma
    "MM": "Multiple myeloma",
    "R/R MM": "Multiple myeloma",
    "RRMM": "Multiple myeloma",
    "relapsed/refractory multiple myeloma": "Multiple myeloma",
    "NDMM": "Multiple myeloma",
    "newly diagnosed multiple myeloma": "Multiple myeloma",

    # Prostate cancer
    "mCRPC": "Prostate cancer",
    "metastatic castration-resistant prostate cancer": "Prostate cancer",
    "HSPC": "Prostate cancer",
    "hormone-sensitive prostate cancer": "Prostate cancer",
    "t-NEPC": "Prostate cancer",  # Treatment-emergent neuroendocrine prostate cancer
    "treatment-emergent neuroendocrine prostate cancer": "Prostate cancer",

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
    "HNSCC": "Head & neck",
    "head and neck": "Head & neck",
    "head & neck": "Head & neck",

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

    # Myeloproliferative neoplasms (MPNs)
    "MPN": "MPN",
    "myeloproliferative neoplasm": "MPN",
    "myeloproliferative neoplasms": "MPN",
    "myeloproliferative disorder": "MPN",
    "myeloproliferative disorders": "MPN",
    "PV": "PV",
    "polycythemia vera": "PV",
    "polycythemia": "PV",
    "ET": "ET",
    "essential thrombocythemia": "ET",
    "essential thrombocytosis": "ET",
    "MF": "MF",
    "myelofibrosis": "MF",
    "primary myelofibrosis": "MF",
    "PMF": "MF",

    # Rare hematologic malignancies
    "BPDCN": "BPDCN",
    "blastic plasmacytoid dendritic cell neoplasm": "BPDCN",

    # Skin cancers
    "BCC": "Basal cell carcinoma",
    "basal cell carcinoma": "Basal cell carcinoma",
    "cSCC": "Cutaneous squamous cell carcinoma",
    "cutaneous squamous cell carcinoma": "Cutaneous squamous cell carcinoma",
    "cutaneous SCC": "Cutaneous squamous cell carcinoma",

    # Neuroendocrine tumors (use singular forms)
    "EP-NEC": "EP-NEC",
    "EP-NECs": "EP-NEC",
    "extra-pulmonary neuroendocrine carcinoma": "EP-NEC",
    "extra-pulmonary NEC": "EP-NEC",
    "extrapulmonary neuroendocrine carcinoma": "EP-NEC",
    "GEP-NET": "GEP-NET",
    "GEP-NETs": "GEP-NET",
    "gastroenteropancreatic neuroendocrine tumor": "GEP-NET",
    "gastroenteropancreatic NET": "GEP-NET",
    "LCNEC": "LCNEC",
    "large cell neuroendocrine carcinoma": "LCNEC",
    "large-cell neuroendocrine carcinoma": "LCNEC",

    # T-cell lymphomas
    "CTCL": "CTCL",
    "cutaneous T-cell lymphoma": "CTCL",
    "cutaneous t-cell lymphoma": "CTCL",
    "mycosis fungoides": "CTCL",
    "Sézary syndrome": "CTCL",
    "sezary syndrome": "CTCL",

    # Chronic myelomonocytic leukemia
    "CMML": "CMML",
    "chronic myelomonocytic leukemia": "CMML",

    # Paraneoplastic syndromes
    "LEMS": "LEMS",
    "Lambert-Eaton": "LEMS",
    "Lambert-Eaton myasthenic syndrome": "LEMS",
    "lambert-eaton myasthenic syndrome": "LEMS",
    "lambert eaton": "LEMS",

    # NF1-associated tumors
    "NF1 plexiform neurofibroma": "NF1-associated plexiform neurofibroma",
    "NF1-associated plexiform neurofibroma": "NF1-associated plexiform neurofibroma",
    "plexiform neurofibroma": "NF1-associated plexiform neurofibroma",
    "neurofibromatosis type 1": "NF1-associated plexiform neurofibroma",

    # Disease hierarchy roll-ups (subtypes → parent disease_state)
    # GIST → Sarcoma (GIST is a disease_type, not disease_state)
    "GIST": "Sarcoma",
    "gastrointestinal stromal tumor": "Sarcoma",
    "gastrointestinal stromal tumour": "Sarcoma",

    # Cholangiocarcinoma → Hepatobiliary cancer
    "cholangiocarcinoma": "Hepatobiliary cancer",
    "CCA": "Hepatobiliary cancer",
    "iCCA": "Hepatobiliary cancer",  # intrahepatic cholangiocarcinoma
    "eCCA": "Hepatobiliary cancer",  # extrahepatic cholangiocarcinoma
    "intrahepatic cholangiocarcinoma": "Hepatobiliary cancer",
    "extrahepatic cholangiocarcinoma": "Hepatobiliary cancer",
    "bile duct cancer": "Hepatobiliary cancer",
    "biliary tract cancer": "Hepatobiliary cancer",
    "BTC": "Hepatobiliary cancer",

    # Gallbladder carcinoma → Hepatobiliary cancer
    "gallbladder cancer": "Hepatobiliary cancer",
    "gallbladder carcinoma": "Hepatobiliary cancer",
}

# Disease subtype mappings
# Maps disease subtypes/histological types to canonical disease states
# NOTE: Subtypes go in disease_type field; disease_state uses parent category
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

    # Sarcoma subtypes (disease_state = "Sarcoma", disease_type = subtype)
    "GIST": "Sarcoma",
    "gastrointestinal stromal tumor": "Sarcoma",
    "gastrointestinal stromal tumour": "Sarcoma",
    "leiomyosarcoma": "Sarcoma",
    "liposarcoma": "Sarcoma",
    "rhabdomyosarcoma": "Sarcoma",
    "synovial sarcoma": "Sarcoma",
    "osteosarcoma": "Sarcoma",
    "Ewing sarcoma": "Sarcoma",
    "chondrosarcoma": "Sarcoma",
    "undifferentiated pleomorphic sarcoma": "Sarcoma",
    "UPS": "Sarcoma",

    # Hepatobiliary cancer subtypes (disease_state = "Hepatobiliary cancer", disease_type = subtype)
    "cholangiocarcinoma": "Hepatobiliary cancer",
    "CCA": "Hepatobiliary cancer",
    "iCCA": "Hepatobiliary cancer",
    "eCCA": "Hepatobiliary cancer",
    "intrahepatic cholangiocarcinoma": "Hepatobiliary cancer",
    "extrahepatic cholangiocarcinoma": "Hepatobiliary cancer",
    "bile duct cancer": "Hepatobiliary cancer",
    "biliary tract cancer": "Hepatobiliary cancer",
    "BTC": "Hepatobiliary cancer",
    "gallbladder cancer": "Hepatobiliary cancer",
    "gallbladder carcinoma": "Hepatobiliary cancer",

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

# Multispecialty Keywords (classify as NON-ONCOLOGY even in cancer context)
# These conditions are managed by non-oncology specialists
MULTISPECIALTY_KEYWORDS = [
    # Cardio-oncology toxicities
    "ici myocarditis",
    "immune checkpoint inhibitor myocarditis",
    "cardio-oncology",
    "cardiotoxicity",
    "cardiac toxicity",

    # Transplant-associated conditions
    "ta-tma",
    "hsct-tma",
    "transplant-associated thrombotic microangiopathy",
    "transplant associated thrombotic microangiopathy",

    # Screening/Risk assessment (primary care audience)
    "prostate cancer screening",
    "psa screening",
    "isopsa",
    "4kscore",
    "prostate risk assessment",

    # Hematology conditions (non-malignant)
    "cold agglutinin syndrome",
    "cold agglutinin disease",
    "cas",
    "cad",
    "autoimmune hemolytic anemia",
    "aiha",

    # Supportive care (non-oncology specialists)
    "iron deficiency anemia",
    "ida",
    "ferric carboxymaltose",
    "fcm",
    "darbepoetin",
    "erythropoietin",
    "epo",
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
    "heme": "Heme malignancies",
    "hematologic": "Heme malignancies",
    "hematological": "Heme malignancies",
    "lymphoma": "DLBCL",  # Default
    "leukemia": "AML",  # Default
    "myeloma": "Multiple myeloma",

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
# NOTE: Consolidation, Maintenance, Perioperative are treatment_line values (not treatment_setting)
VALID_TREATMENT_LINES = {
    "early_stage": ["Adjuvant", "Neoadjuvant", "Perioperative"],
    "metastatic": ["1L", "2L+", "Maintenance", "Consolidation"],
    "hematologic": ["Newly diagnosed", "R/R", "Maintenance", "Bridging", "Consolidation"],
    "gvhd": ["Steroid-naive", "Steroid-refractory", "Prophylaxis"],
}

# ============================================================================
# EXPANDED FIELD CANONICAL VALUES (Groups A-F)
# ============================================================================

# === GROUP A: Treatment Metadata ===

DRUG_CLASSES = [
    # Targeted Therapies
    "CDK4/6 inhibitor",
    "EGFR TKI",
    "ALK inhibitor",
    "ROS1 inhibitor",
    "KRAS G12C inhibitor",
    "BRAF inhibitor",
    "MEK inhibitor",
    "HER2 TKI",
    "BTK inhibitor",
    "BCL-2 inhibitor",
    "PI3K inhibitor",
    "AKT inhibitor",
    "PARP inhibitor",
    "FLT3 inhibitor",
    "IDH inhibitor",
    "JAK inhibitor",
    "Menin inhibitor",
    "FGFR inhibitor",
    "MET inhibitor",
    "RET inhibitor",
    "NTRK inhibitor",
    "XPO1 inhibitor",
    "EZH2 inhibitor",
    # Immunotherapy
    "Anti-PD-1",
    "Anti-PD-L1",
    "Anti-CTLA-4",
    "Checkpoint inhibitor combination",
    "CAR-T therapy",
    "Bispecific T-cell engager",
    "Bispecific antibody",
    # ADCs
    "Antibody-drug conjugate (ADC)",
    "HER2-directed ADC",
    "Trop-2-directed ADC",
    "BCMA-directed ADC",
    "CD19-directed ADC",
    "FRα-directed ADC",
    "Nectin-4-directed ADC",
    # Monoclonal Antibodies
    "Anti-CD20 mAb",
    "Anti-CD38 mAb",
    "Anti-HER2 mAb",
    "Anti-EGFR mAb",
    "Anti-VEGF mAb",
    # Hormonal
    "Aromatase inhibitor",
    "SERD",
    "Androgen receptor inhibitor",
    "Androgen synthesis inhibitor",
    # Other
    "IMiD",
    "Proteasome inhibitor",
    "Hypomethylating agent",
    "Chemotherapy",
]

DRUG_TARGETS = [
    "EGFR",
    "ALK",
    "ROS1",
    "RET",
    "MET",
    "NTRK",
    "KRAS G12C",
    "BRAF V600E",
    "HER2",
    "CDK4/6",
    "PIK3CA",
    "AKT",
    "BRCA1/2",
    "PD-1",
    "PD-L1",
    "CTLA-4",
    "LAG-3",
    "TIM-3",
    "CD19",
    "CD20",
    "CD22",
    "CD38",
    "BCMA",
    "GPRC5D",
    "FcRH5",
    "Trop-2",
    "FRα",
    "Nectin-4",
    "BTK",
    "BCL-2",
    "FLT3",
    "IDH1",
    "IDH2",
    "JAK1/2",
    "Menin-KMT2A",
    "FGFR",
    "XPO1",
    "EZH2",
    "VEGF/VEGFR",
    "Androgen receptor",
    "Estrogen receptor",
]

# DEPRECATED: treatment_setting field removed from schema
# Consolidation, Maintenance, Perioperative moved to treatment_line
# TREATMENT_SETTINGS = [
#     "Curative-intent",
#     "Palliative",
#     "Perioperative",
#     "Consolidation",
#     "Maintenance",
#     "Bridging",
#     "Conditioning",
#     "Salvage",
# ]

RESISTANCE_MECHANISMS = [
    "T790M mutation",
    "C797S mutation",
    "MET amplification",
    "HER2 amplification",
    "EGFR amplification",
    "PIK3CA mutation",
    "PTEN loss",
    "TP53 mutation",
    "RB1 loss",
    "ESR1 mutation",
    "ALK resistance mutation",
    "BTK C481S mutation",
    "BCR-ABL T315I",
    "KRAS mutation",
    "NRAS mutation",
    "Histologic transformation",
    "EMT",
    "Lineage plasticity",
]

# === GROUP B: Clinical Context ===

METASTATIC_SITES = [
    "Brain metastases",
    "CNS metastases",
    "Leptomeningeal disease",
    "Bone metastases",
    "Liver metastases",
    "Lung metastases",
    "Lymph node metastases",
    "Peritoneal carcinomatosis",
    "Pleural effusion",
    "Ascites",
    "Skin metastases",
    "Soft tissue metastases",
    "Adrenal metastases",
    "Oligometastatic disease",
]

SYMPTOMS = [
    "Pain",
    "Bone pain",
    "Fatigue",
    "Nausea/vomiting",
    "Dyspnea",
    "Cough",
    "Weight loss",
    "Anorexia",
    "Diarrhea",
    "Constipation",
    "Peripheral neuropathy",
    "Cognitive impairment",
    "Bleeding",
    "Infection",
    "Febrile neutropenia",
]

SPECIAL_POPULATIONS = [
    "Elderly (≥65 years)",
    "Very elderly (≥75 years)",
    "Pediatric",
    "AYA (adolescent/young adult)",
    "Pregnant",
    "Organ dysfunction - Renal",
    "Organ dysfunction - Hepatic",
    "Organ dysfunction - Cardiac",
    "Poor performance status (ECOG ≥2)",
    "Frail",
    "Transplant-eligible",
    "Transplant-ineligible",
    "High-risk cytogenetics",
    "Standard-risk cytogenetics",
    # NOTE: "CNS involvement" removed - use metastatic_site: "Brain metastases" or "Leptomeningeal disease" instead
    "Autoimmune disease",
    "Prior allogeneic transplant",
]

PERFORMANCE_STATUS_VALUES = [
    "ECOG 0",
    "ECOG 1",
    "ECOG 2",
    "ECOG 3",
    "ECOG 4",
    "KPS 100",
    "KPS 90",
    "KPS 80",
    "KPS 70",
    "KPS ≤60",
    "Frail",
    "Fit",
    "Unfit",
]

# === GROUP C: Safety/Toxicity ===

TOXICITY_TYPES = [
    # Immune-related
    "Immune-related colitis",
    "Immune-related hepatitis",
    "Immune-related pneumonitis",
    "Immune-related thyroiditis",
    "Immune-related hypophysitis",
    "Immune-related myocarditis",
    "Immune-related nephritis",
    "Immune-related dermatitis",
    "Immune-related arthritis",
    "Immune-related encephalitis",
    # Hematologic
    "Neutropenia",
    "Febrile neutropenia",
    "Thrombocytopenia",
    "Anemia",
    "Lymphopenia",
    "Pancytopenia",
    # GI
    "Diarrhea",
    "Nausea/vomiting",
    "Mucositis/stomatitis",
    "Hepatotoxicity",
    "Pancreatitis",
    # Cardiac
    "QT prolongation",
    "Cardiomyopathy",
    "Arrhythmia",
    "Hypertension",
    "Pericardial effusion",
    # Pulmonary
    "Interstitial lung disease (ILD)",
    "Pneumonitis",
    # Neurologic
    "Peripheral neuropathy",
    "Neurotoxicity",
    "ICANS",
    "Cognitive dysfunction",
    # CAR-T/Bispecific specific
    "Cytokine release syndrome (CRS)",
    "Tumor lysis syndrome (TLS)",
    "Macrophage activation syndrome",
    # Dermatologic
    "Rash",
    "Hand-foot syndrome",
    "Alopecia",
    "Photosensitivity",
    # Ocular
    "Ocular toxicity",
    "Keratopathy",
    "Blurred vision",
    "Dry eye",
    # Other
    "Fatigue",
    "Infusion-related reaction",
    "Hypersensitivity",
    "Secondary malignancy",
]

TOXICITY_ORGANS = [
    "Cardiac",
    "Pulmonary",
    "Hepatic",
    "Renal",
    "Gastrointestinal",
    "Dermatologic",
    "Neurologic",
    "Ocular",
    "Hematologic",
    "Endocrine",
    "Musculoskeletal",
    "Vascular",
]

TOXICITY_GRADES = [
    "Grade 1",
    "Grade 2",
    "Grade 3",
    "Grade 4",
    "Grade 5",
    "Grade 1-2",
    "Grade ≥3",
    "Any grade",
    "Serious",
    "Dose-limiting",
]

# === GROUP D: Efficacy/Outcomes ===

EFFICACY_ENDPOINTS = [
    # Survival
    "Overall survival (OS)",
    "Progression-free survival (PFS)",
    "Disease-free survival (DFS)",
    "Event-free survival (EFS)",
    "Relapse-free survival (RFS)",
    "Time to progression (TTP)",
    "Duration of response (DOR)",
    # Response
    "Overall response rate (ORR)",
    "Complete response rate (CR)",
    "Partial response rate (PR)",
    "Pathologic complete response (pCR)",
    "Minimal residual disease (MRD)",
    "MRD negativity",
    "Cytogenetic response",
    "Molecular response",
    # Disease control
    "Disease control rate (DCR)",
    "Clinical benefit rate (CBR)",
    "Stable disease (SD)",
    # Quality of life
    "Health-related quality of life (HRQoL)",
    "Patient-reported outcomes (PRO)",
    "Symptom control",
    # Other
    "Time to response (TTR)",
    "Time to next treatment (TTNT)",
    "Treatment-free interval",
    "Biomarker response",
]

OUTCOME_CONTEXTS = [
    "Primary endpoint met",
    "Primary endpoint not met",
    "Secondary endpoint",
    "Exploratory endpoint",
    "Subgroup analysis",
    "Post-hoc analysis",
    "Interim analysis",
    "Final analysis",
    "Updated analysis",
    "Long-term follow-up",
    "Real-world evidence",
]

CLINICAL_BENEFITS = [
    "Statistically significant",
    "Clinically meaningful",
    "Non-inferior",
    "Superior",
    "Trend toward benefit",
    "No significant difference",
    "Detrimental",
    "Hazard ratio",
    "Absolute benefit",
    "Relative risk reduction",
]

# === GROUP E: Evidence/Guidelines ===

GUIDELINE_SOURCES = [
    "NCCN",
    "ASCO",
    "ESMO",
    "ASH",
    "ELN",
    "IMWG",
    "IWCLL",
    "FDA label",
    "EMA label",
    "ASTRO",
    "AUA",
    "ISTH",
    "Expert consensus",
]

EVIDENCE_TYPES = [
    "Phase 3 RCT",
    "Phase 2 RCT",
    "Phase 1/2 trial",
    "Phase 1 trial",
    "Single-arm trial",
    "Real-world evidence",
    "Retrospective study",
    "Meta-analysis",
    "Systematic review",
    "Case series",
    "Expert opinion",
    "Guideline recommendation",
]

# DEPRECATED: trial_phase removed - captured by evidence_type (e.g., "Phase 3 RCT")
# TRIAL_PHASES = ["Phase 1", "Phase 1/2", "Phase 2", "Phase 2/3", "Phase 3", "Phase 4", "Post-marketing"]

# === GROUP F: Question Format/Quality ===

CME_OUTCOME_LEVELS = [
    "3 - Knowledge",      # Can recall/recognize information
    "4 - Competence",     # Can demonstrate application of knowledge
]

DATA_RESPONSE_TYPES = [
    "Numeric",            # Specific number (e.g., "What was the ORR?")
    "Qualitative",        # Descriptive (e.g., "Which best describes...")
    "Comparative",        # Comparing options (e.g., "Which is preferred?")
    "Boolean",            # Yes/No (e.g., "Is X approved for...?")
]

# DEPRECATED: endpoint_type removed - captured by outcome_context
# ENDPOINT_TYPES = ["Primary", "Key secondary", "Secondary", "Exploratory", "Subgroup", "Post-hoc"]

# === Question Structure Fields (NEW) ===

STEM_TYPES = [
    "Clinical vignette",      # Patient case scenario
    "Direct question",        # Straightforward question without case
    "Incomplete statement",   # "The mechanism of X is..."
]

LEAD_IN_TYPES = [
    "Standard",               # "Which of the following..."
    "Negative (EXCEPT/NOT)",  # "All EXCEPT...", "Which is NOT..."
    "Best answer",            # "What is the BEST...", "most appropriate"
    "True statement",         # "Which statement is TRUE..."
]

ANSWER_FORMATS = [
    "Single best",            # Standard single correct answer
    "Compound (A+B)",         # "A and B", "Both A and C"
    "All of above",           # "All of the above" as an option
    "None of above",          # "None of the above" as an option
    "True-False",             # True/False format
]

ANSWER_LENGTH_PATTERNS = [
    "Uniform",                # All options similar length
    "Correct longest",        # Correct answer noticeably longer (testwise cue)
    "Correct shortest",       # Correct answer noticeably shorter (testwise cue)
    "Variable",               # Mixed lengths, no pattern
]

DISTRACTOR_HOMOGENEITY_VALUES = [
    "Homogeneous",            # All options from same category/theme
    "Heterogeneous",          # Options from different categories (allows elimination)
]

# Item writing flaw fields are booleans (true/false), no canonical list needed
# - flaw_absolute_terms: "always", "never", "all", "none" in options
# - flaw_grammatical_cue: stem grammar reveals answer (a/an, singular/plural)
# - flaw_implausible_distractor: obviously wrong options
# - flaw_clang_association: answer shares unusual words with stem
# - flaw_convergence_vulnerability: correct answer has elements from multiple options
# - flaw_double_negative: negative stem + negative option
