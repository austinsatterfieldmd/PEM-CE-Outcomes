/**
 * Field guidance configuration for the tag editor.
 * Provides descriptions, examples, and allowed values for all 70 tag fields.
 */

export interface FieldGuidanceInfo {
  description: string
  examples?: string[]
  allowedValues?: string[]
  note?: string
}

export const FIELD_GUIDANCE: Record<string, FieldGuidanceInfo> = {
  // ============================================
  // CORE CLASSIFICATION (4 fields)
  // ============================================
  topic: {
    description: "The primary educational focus of the question",
    allowedValues: [
      "Treatment selection",
      "Treatment indication",
      "Clinical efficacy",
      "Safety profile",
      "AE management",
      "Biomarker testing",
      "Mechanism of action",
      "Diagnosis",
      "Prognosis",
      "Study design",
      "Multidisciplinary care",
      "Disparities in care",
      "Barriers to care",
    ],
    note: "Every question must have exactly one topic",
  },

  disease_state: {
    description: "The specific cancer/disease type (use canonical naming)",
    allowedValues: [
      // Solid tumors - Thoracic
      "NSCLC",
      "SCLC",
      "Mesothelioma",
      // Solid tumors - Breast
      "Breast cancer",
      // Solid tumors - GI
      "CRC",
      "Gastric cancer",
      "Esophageal cancer",
      "Gastroesophageal junction cancer",
      "Hepatocellular carcinoma",
      "Cholangiocarcinoma",
      "Pancreatic cancer",
      // Solid tumors - GU
      "Prostate cancer",
      "Bladder cancer",
      "Renal cell carcinoma",
      "Testicular cancer",
      // Solid tumors - GYN
      "Ovarian cancer",
      "Endometrial cancer",
      "Cervical cancer",
      // Solid tumors - Head & Neck
      "Head and neck cancer",
      "Thyroid cancer",
      // Solid tumors - Skin
      "Melanoma",
      "Merkel cell carcinoma",
      "Basal cell carcinoma",
      "Cutaneous squamous cell carcinoma",
      // Solid tumors - CNS
      "Glioblastoma",
      "Brain metastases",
      // Solid tumors - Sarcoma
      "Soft tissue sarcoma",
      "Osteosarcoma",
      "GIST",
      // Hematologic - Plasma cell
      "Multiple myeloma",
      "Amyloidosis",
      "Waldenstrom macroglobulinemia",
      // Hematologic - Lymphoma
      "DLBCL",
      "Follicular lymphoma",
      "Mantle cell lymphoma",
      "Marginal zone lymphoma",
      "Hodgkin lymphoma",
      "T-cell lymphoma",
      // Hematologic - Leukemia
      "CLL",
      "AML",
      "ALL",
      "CML",
      // Hematologic - Myeloid
      "MDS",
      "MPN",
      "Myelofibrosis",
    ],
    note: "Use canonical disease names. Subtypes go in disease_type_1/2",
  },

  disease_state_1: {
    description: "Primary disease state (the main cancer/disease type)",
    allowedValues: [
      // Same as disease_state - duplicated for clarity in numbered field pattern
      "NSCLC", "SCLC", "Mesothelioma", "Breast cancer", "CRC", "Gastric cancer",
      "Esophageal cancer", "Gastroesophageal junction cancer", "Hepatocellular carcinoma",
      "Cholangiocarcinoma", "Pancreatic cancer", "Prostate cancer", "Bladder cancer",
      "Renal cell carcinoma", "Testicular cancer", "Ovarian cancer", "Endometrial cancer",
      "Cervical cancer", "Head and neck cancer", "Thyroid cancer", "Melanoma",
      "Merkel cell carcinoma", "Basal cell carcinoma", "Cutaneous squamous cell carcinoma",
      "Glioblastoma", "Brain metastases", "Soft tissue sarcoma", "Osteosarcoma", "GIST",
      "Multiple myeloma", "Amyloidosis", "Waldenstrom macroglobulinemia", "DLBCL",
      "Follicular lymphoma", "Mantle cell lymphoma", "Marginal zone lymphoma",
      "Hodgkin lymphoma", "T-cell lymphoma", "CLL", "AML", "ALL", "CML", "MDS", "MPN", "Myelofibrosis",
    ],
    note: "Required field. Most questions have only one disease state.",
  },

  disease_state_2: {
    description: "Secondary disease state (rare: for questions covering two distinct diseases, e.g., MM + NHL)",
    allowedValues: [],  // Inherits from disease_state_1
    note: "Rare. Only use when question genuinely covers two distinct disease states.",
  },

  disease_stage: {
    description: "Cancer stage at presentation",
    allowedValues: [
      // Solid tumors
      "Early-stage",
      "Early-stage resectable",
      "Early-stage unresectable",
      "Metastatic",
      // SCLC
      "Limited-stage",
      "Extensive-stage",
      // Multiple myeloma (R-ISS)
      "R-ISS I",
      "R-ISS II",
      "R-ISS III",
      // Lymphoma (Ann Arbor)
      "Ann Arbor I",
      "Ann Arbor II",
      "Ann Arbor III",
      "Ann Arbor IV",
      // CLL (Rai)
      "Rai 0",
      "Rai I-II",
      "Rai III-IV",
      // CLL (Binet)
      "Binet A",
      "Binet B",
      "Binet C",
    ],
    note: "Solid tumors: Early-stage (resectable/unresectable)/Metastatic. SCLC: Limited/Extensive-stage. MM: R-ISS. Lymphoma: Ann Arbor. CLL: Rai or Binet",
  },

  disease_type_1: {
    description: "Histologic or receptor subtype (NOT molecular biomarkers)",
    allowedValues: [
      // Breast cancer subtypes
      "HER2+",
      "HR+/HER2-",
      "Triple-negative",
      "HER2-low",
      // NSCLC histology
      "Squamous",
      "Non-squamous",
      "Adenocarcinoma",
      "Large cell",
      // GI subtypes
      "MSI-H/dMMR",
      "MSS/pMMR",
      // Prostate
      "Castration-sensitive",
      "Castration-resistant",
      // Ovarian
      "High-grade serous",
      "Low-grade serous",
      "Clear cell",
      "Endometrioid",
      // Lymphoma
      "GCB",
      "Non-GCB/ABC",
      "Double-hit",
      "Triple-hit",
      // General
      "De novo",
      "Transformed",
    ],
    note: "NSCLC: Squamous vs Non-squamous/Adenocarcinoma. Breast: HER2+, HR+/HER2-, TNBC. Molecular markers (EGFR, ALK, ROS1) go in biomarker fields",
  },

  disease_type_2: {
    description: "Secondary histologic/receptor subtype if applicable",
    allowedValues: [
      // Risk stratification
      "High-risk",
      "Standard-risk",
      "Low-risk",
      "Intermediate-risk",
      "Very high-risk",
      // Breast cancer secondary
      "HER2-low",
      "HR+",
      "HR-",
      // Stage modifiers
      "Locally advanced",
      "Oligometastatic",
      // Heme modifiers
      "Primary refractory",
      "Early relapse",
      "Late relapse",
    ],
    note: "Use for secondary classification. Transplant eligibility goes in treatment_eligibility field",
  },

  treatment_line: {
    description: "Line of therapy",
    allowedValues: [
      // Metastatic solid tumors
      "1L",
      "2L+",
      "Maintenance",
      // Early-stage solid tumors
      "Adjuvant",
      "Neoadjuvant",
      "Perioperative",
      // Unresectable/locally advanced or post-induction
      "Consolidation",
      // Hematologic malignancies
      "Newly diagnosed",
      "R/R",
      "Bridging",
    ],
    note: "Metastatic solid: 1L/2L+/Maintenance. Early-stage: Adjuvant/Neoadjuvant/Perioperative. Unresectable/post-induction: Consolidation. Heme: Newly diagnosed/R/R/Bridging",
  },

  // ============================================
  // MULTI-VALUE FIELDS (15 fields)
  // ============================================
  treatment_1: {
    description: "Primary drug/regimen name (fundable drugs only)",
    allowedValues: [
      // PD-1/PD-L1 inhibitors
      "Pembrolizumab",
      "Nivolumab",
      "Atezolizumab",
      "Durvalumab",
      "Cemiplimab",
      // CTLA-4 inhibitors
      "Ipilimumab",
      "Tremelimumab",
      // HER2-targeted
      "Trastuzumab",
      "Pertuzumab",
      "Trastuzumab deruxtecan",
      "Trastuzumab emtansine",
      "Tucatinib",
      "Neratinib",
      "Margetuximab",
      // EGFR TKIs
      "Osimertinib",
      "Erlotinib",
      "Gefitinib",
      "Afatinib",
      "Dacomitinib",
      "Amivantamab",
      // ALK/ROS1 TKIs
      "Alectinib",
      "Brigatinib",
      "Lorlatinib",
      "Crizotinib",
      "Ceritinib",
      // KRAS G12C inhibitors
      "Sotorasib",
      "Adagrasib",
      // CDK4/6 inhibitors
      "Palbociclib",
      "Ribociclib",
      "Abemaciclib",
      // PARP inhibitors
      "Olaparib",
      "Niraparib",
      "Rucaparib",
      "Talazoparib",
      // Anti-VEGF
      "Bevacizumab",
      "Ramucirumab",
      // Multi-kinase TKIs
      "Lenvatinib",
      "Cabozantinib",
      "Regorafenib",
      "Sorafenib",
      "Sunitinib",
      "Pazopanib",
      "Axitinib",
      // ADCs
      "Sacituzumab govitecan",
      "Enfortumab vedotin",
      "Tisotumab vedotin",
      "Mirvetuximab soravtansine",
      // Multiple myeloma
      "Daratumumab",
      "Isatuximab",
      "Elotuzumab",
      "Bortezomib",
      "Carfilzomib",
      "Ixazomib",
      "Lenalidomide",
      "Pomalidomide",
      "Selinexor",
      "Belantamab mafodotin",
      "Teclistamab",
      "Elranatamab",
      "Talquetamab",
      "Ciltacabtagene autoleucel",
      "Idecabtagene vicleucel",
      // CLL/Lymphoma
      "Ibrutinib",
      "Acalabrutinib",
      "Zanubrutinib",
      "Venetoclax",
      "Rituximab",
      "Obinutuzumab",
      "Polatuzumab vedotin",
      "Loncastuximab tesirine",
      "Mosunetuzumab",
      "Epcoritamab",
      "Glofitamab",
      "Axicabtagene ciloleucel",
      "Tisagenlecleucel",
      "Lisocabtagene maraleucel",
      // AML
      "Venetoclax",
      "Gilteritinib",
      "Midostaurin",
      "Ivosidenib",
      "Enasidenib",
      "Gemtuzumab ozogamicin",
      // Hormone therapies
      "Enzalutamide",
      "Abiraterone",
      "Apalutamide",
      "Darolutamide",
      // Other targeted
      "Encorafenib",
      "Dabrafenib",
      "Vemurafenib",
      "Trametinib",
      "Cobimetinib",
      "Binimetinib",
      "Larotrectinib",
      "Entrectinib",
      "Pralsetinib",
      "Selpercatinib",
      "Capmatinib",
      "Tepotinib",
      "Tivozanib",
      "Alpelisib",
      "Elacestrant",
      "Capivasertib",
    ],
    note: "Capitalize first letter. Only tag targeted therapies, ADCs, immunotherapies. DO NOT tag chemotherapy, radiation, or surgery",
  },

  treatment_2: {
    description: "Secondary treatment if multiple fundable drugs",
    allowedValues: [], // Same values as treatment_1, handled by component
    note: "Same drug list as treatment_1",
  },

  treatment_3: {
    description: "Third treatment if applicable",
    allowedValues: [], // Same values as treatment_1
  },

  treatment_4: {
    description: "Fourth treatment if applicable",
    allowedValues: [], // Same values as treatment_1
  },

  treatment_5: {
    description: "Fifth treatment if applicable",
    allowedValues: [], // Same values as treatment_1
  },

  biomarker_1: {
    description: "Primary biomarker or molecular alteration",
    allowedValues: [
      // NSCLC driver mutations
      "EGFR",
      "EGFR exon 19 del",
      "EGFR L858R",
      "EGFR exon 20 ins",
      "T790M",
      "C797S",
      "ALK",
      "ROS1",
      "KRAS G12C",
      "KRAS",
      "MET exon 14 skipping",
      "MET amplification",
      "RET",
      "BRAF V600E",
      "NTRK",
      "HER2 mutation",
      "NRG1",
      // PD-L1 expression
      "PD-L1 >=50%",
      "PD-L1 1-49%",
      "PD-L1 <1%",
      "PD-L1",
      // Breast cancer biomarkers
      "BRCA1",
      "BRCA2",
      "BRCA1/2",
      "HRD",
      "PIK3CA",
      "ESR1",
      "HER2",
      "ER",
      "PR",
      // GI biomarkers
      "MSI-H",
      "dMMR",
      "MSS",
      "pMMR",
      "BRAF",
      "NRAS",
      "HER2 amplification",
      "FGFR2",
      "Claudin 18.2",
      // Prostate biomarkers
      "BRCA",
      "ATM",
      "CDK12",
      "HRR mutation",
      // Hematologic biomarkers
      "FLT3-ITD",
      "FLT3-TKD",
      "NPM1",
      "IDH1",
      "IDH2",
      "TP53",
      "del(17p)",
      "t(4;14)",
      "t(11;14)",
      "t(14;16)",
      "gain(1q)",
      "MYC rearrangement",
      "BCL2 rearrangement",
      "BCL6 rearrangement",
      // General
      "TMB-H",
      "ctDNA",
      "MRD positive",
      "MRD negative",
    ],
    note: "NSCLC: EGFR, ALK, ROS1, KRAS G12C go HERE (not in disease_type). Avoid redundancy with disease_type (e.g., don't tag HER2 if disease_type is HER2+)",
  },

  biomarker_2: {
    description: "Secondary biomarker",
    allowedValues: [], // Same values as biomarker_1
  },

  biomarker_3: {
    description: "Third biomarker",
    allowedValues: [], // Same values as biomarker_1
  },

  biomarker_4: {
    description: "Fourth biomarker",
    allowedValues: [], // Same values as biomarker_1
  },

  biomarker_5: {
    description: "Fifth biomarker",
    allowedValues: [], // Same values as biomarker_1
  },

  trial_1: {
    description: "Clinical trial name if explicitly mentioned or confidently inferable",
    allowedValues: [
      // NSCLC trials
      "KEYNOTE-024",
      "KEYNOTE-042",
      "KEYNOTE-189",
      "KEYNOTE-407",
      "KEYNOTE-671",
      "CheckMate 816",
      "CheckMate 227",
      "CheckMate 9LA",
      "IMpower110",
      "IMpower150",
      "PACIFIC",
      "ADAURA",
      "FLAURA",
      "FLAURA2",
      "CROWN",
      "ALEX",
      "CodeBreaK 200",
      "KRYSTAL-1",
      "LIBRETTO-001",
      "GEOMETRY mono-1",
      // Breast cancer trials
      "DESTINY-Breast03",
      "DESTINY-Breast04",
      "CLEOPATRA",
      "APHINITY",
      "KATHERINE",
      "KEYNOTE-522",
      "monarchE",
      "NATALEE",
      "PALOMA-3",
      "MONALEESA-7",
      "OlympiA",
      "OlympiAD",
      "EMBRACA",
      "TROPiCS-02",
      "ASCENT",
      "CAPItello-291",
      // GI trials
      "KEYNOTE-859",
      "CheckMate 649",
      "KEYNOTE-177",
      "CheckMate 142",
      "BEACON",
      // GU trials
      "KEYNOTE-564",
      "CheckMate 274",
      "KEYNOTE-426",
      "CheckMate 9ER",
      "CLEAR",
      "ARCHES",
      "TITAN",
      "ENZAMET",
      "PROfound",
      // Multiple myeloma trials
      "CASSIOPEIA",
      "GRIFFIN",
      "MAIA",
      "ALCYONE",
      "POLLUX",
      "CASTOR",
      "CARTITUDE-1",
      "CARTITUDE-4",
      "KarMMa",
      "KarMMa-3",
      "MajesTEC-1",
      "MonumenTAL-1",
      // Lymphoma trials
      "POLARIX",
      "ZUMA-1",
      "ZUMA-7",
      "JULIET",
      "TRANSFORM",
      // CLL trials
      "RESONATE-2",
      "ELEVATE-TN",
      "ALPINE",
      "CLL14",
      // AML trials
      "VIALE-A",
      "ADMIRAL",
      "QUAZAR",
    ],
    note: "Only tag if trial is mentioned or confidently inferable from drug + indication + endpoints",
  },

  trial_2: {
    description: "Secondary trial",
    allowedValues: [], // Same values as trial_1
  },

  trial_3: {
    description: "Third trial",
    allowedValues: [], // Same values as trial_1
  },

  trial_4: {
    description: "Fourth trial",
    allowedValues: [], // Same values as trial_1
  },

  trial_5: {
    description: "Fifth trial",
    allowedValues: [], // Same values as trial_1
  },

  // ============================================
  // PATIENT CHARACTERISTICS (8 fields)
  // ============================================
  treatment_eligibility: {
    description: "Treatment eligibility status",
    allowedValues: [
      "Transplant-eligible",
      "Transplant-ineligible",
      "CAR-T eligible",
      "CAR-T ineligible",
    ],
    note: "For heme malignancies (MM, lymphoma). Captures fitness for intensive treatment approaches",
  },

  age_group: {
    description: "Patient age category",
    allowedValues: ["Pediatric", "AYA", "Young", "Transitional", "Elderly"],
    note: "Pediatric: <18 (<15 for ALL), AYA: 15-39 (ALL), Young: <65, Transitional: 65-75, Elderly: 75+",
  },

  organ_dysfunction: {
    description: "Organ dysfunction affecting treatment",
    allowedValues: ["Renal", "Hepatic", "Cardiac"],
    note: "Organ impairment that affects drug dosing or treatment selection",
  },

  fitness_status: {
    description: "Patient fitness level (categorical, not ECOG)",
    allowedValues: ["Fit", "Unfit", "Frail"],
    note: "Use for fitness categories. ECOG scores go in performance_status field",
  },

  disease_specific_factor: {
    description: "Disease-specific clinical factor NOT captured elsewhere",
    allowedValues: [
      // Cytogenetics/risk factors
      "High-risk cytogenetics",
      "Standard-risk cytogenetics",
      "Favorable cytogenetics",
      "Adverse cytogenetics",
      "Complex karyotype",
      // Myeloma-specific
      "Extramedullary disease",
      "Plasma cell leukemia",
      "High tumor burden",
      "Renal involvement",
      // Lymphoma-specific
      "Bulky disease",
      "B symptoms",
      "CNS involvement",
      "Bone marrow involvement",
      // Solid tumor factors
      "Visceral crisis",
      "Rapid progression",
      "Indolent disease",
      // General
      "Prior stem cell transplant",
      "Prior CAR-T therapy",
      "Primary refractory",
    ],
    note: "For factors that don't fit in disease_type, disease_stage, or biomarker. Staging (R-ISS, Ann Arbor) goes in disease_stage",
  },

  comorbidity_1: {
    description: "Primary comorbidity affecting treatment decisions",
    allowedValues: [
      // Cardiovascular
      "Hypertension",
      "Heart failure",
      "Coronary artery disease",
      "Atrial fibrillation",
      "Peripheral vascular disease",
      // Metabolic
      "Diabetes",
      "Obesity",
      "Dyslipidemia",
      // Pulmonary
      "COPD",
      "Asthma",
      "Interstitial lung disease",
      // Renal
      "Chronic kidney disease",
      "Renal insufficiency",
      // Hepatic
      "Cirrhosis",
      "Chronic hepatitis",
      // Autoimmune
      "Autoimmune disease",
      "Rheumatoid arthritis",
      "Inflammatory bowel disease",
      // Other
      "Prior malignancy",
      "Osteoporosis",
      "Neuropathy",
      "Depression/anxiety",
    ],
  },

  comorbidity_2: {
    description: "Secondary comorbidity",
    allowedValues: [], // Same values as comorbidity_1
  },

  comorbidity_3: {
    description: "Third comorbidity",
    allowedValues: [], // Same values as comorbidity_1
  },

  // ============================================
  // TREATMENT METADATA (10 fields)
  // ============================================
  drug_class_1: {
    description: "Therapeutic class of primary drug",
    allowedValues: [
      // Checkpoint inhibitors
      "Anti-PD-1",
      "Anti-PD-L1",
      "Anti-CTLA-4",
      // Targeted therapies
      "EGFR TKI",
      "ALK TKI",
      "ROS1 TKI",
      "KRAS G12C inhibitor",
      "MET inhibitor",
      "RET inhibitor",
      "NTRK inhibitor",
      "BRAF inhibitor",
      "MEK inhibitor",
      "HER2 TKI",
      "CDK4/6 inhibitor",
      "PARP inhibitor",
      "PI3K inhibitor",
      "AKT inhibitor",
      "SERD",
      "BTK inhibitor",
      "BCL-2 inhibitor",
      "FLT3 inhibitor",
      "IDH inhibitor",
      "Proteasome inhibitor",
      "IMiD",
      "XPO1 inhibitor",
      // Antibodies
      "Anti-HER2",
      "Anti-CD38",
      "Anti-CD20",
      "Anti-VEGF",
      "Anti-VEGFR",
      "Anti-BCMA",
      "Anti-GPRC5D",
      // Advanced modalities
      "Antibody-drug conjugate (ADC)",
      "CAR-T therapy",
      "Bispecific T-cell engager",
      // Hormone therapy
      "Androgen receptor inhibitor",
      "CYP17 inhibitor",
      "Aromatase inhibitor",
      // Multi-kinase
      "Multi-kinase TKI",
    ],
  },

  drug_class_2: {
    description: "Therapeutic class of secondary drug",
    allowedValues: [], // Same values as drug_class_1
  },

  drug_class_3: {
    description: "Therapeutic class of third drug",
    allowedValues: [], // Same values as drug_class_1
  },

  drug_target_1: {
    description: "Molecular target of primary drug",
    allowedValues: [
      // Immune targets
      "PD-1",
      "PD-L1",
      "CTLA-4",
      "LAG-3",
      // Kinase targets
      "EGFR",
      "ALK",
      "ROS1",
      "KRAS G12C",
      "MET",
      "RET",
      "NTRK",
      "BRAF",
      "MEK",
      "HER2",
      "HER3",
      "CDK4/6",
      "PI3K",
      "AKT",
      "mTOR",
      "FGFR",
      // DNA repair
      "PARP",
      // Hormone receptors
      "ER",
      "AR",
      "CYP17",
      // Hematologic targets
      "BTK",
      "BCL-2",
      "FLT3",
      "IDH1",
      "IDH2",
      "Proteasome",
      "Cereblon",
      "XPO1",
      // Cell surface targets
      "BCMA",
      "CD38",
      "CD20",
      "CD19",
      "CD22",
      "GPRC5D",
      "FcRH5",
      // Angiogenesis
      "VEGF",
      "VEGFR",
      // Other
      "Trop-2",
      "Nectin-4",
      "Tissue factor",
      "FRα",
    ],
  },

  drug_target_2: {
    description: "Molecular target of secondary drug",
    allowedValues: [], // Same values as drug_target_1
  },

  drug_target_3: {
    description: "Molecular target of third drug",
    allowedValues: [], // Same values as drug_target_1
  },

  prior_therapy_1: {
    description: "Prior treatment mentioned as context",
    allowedValues: [
      // By class
      "Prior immunotherapy",
      "Prior PD-1/PD-L1 inhibitor",
      "Prior EGFR TKI",
      "Prior ALK TKI",
      "Prior CDK4/6 inhibitor",
      "Prior PARP inhibitor",
      "Prior BTK inhibitor",
      "Prior PI3K inhibitor",
      "Prior proteasome inhibitor",
      "Prior IMiD",
      "Prior anti-CD38",
      "Prior CAR-T",
      "Prior bispecific",
      // By specific drug
      "Prior trastuzumab",
      "Prior platinum",
      "Prior taxane",
      "Prior anthracycline",
      // By modality
      "Prior chemotherapy",
      "Prior hormonal therapy",
      "Prior radiation",
      "Prior stem cell transplant",
    ],
  },

  prior_therapy_2: {
    description: "Secondary prior treatment",
    allowedValues: [], // Same values as prior_therapy_1
  },

  prior_therapy_3: {
    description: "Third prior treatment",
    allowedValues: [], // Same values as prior_therapy_1
  },

  resistance_mechanism: {
    description: "Specific resistance mechanism mentioned",
    allowedValues: [
      // EGFR resistance
      "T790M mutation",
      "C797S mutation",
      "MET amplification",
      "HER2 amplification",
      "EGFR amplification",
      "Small cell transformation",
      "Squamous transformation",
      // Breast cancer resistance
      "ESR1 mutation",
      "PIK3CA mutation",
      "HER2 loss",
      // Hematologic resistance
      "BTK C481S mutation",
      "BCL2 mutation",
      "TP53 mutation",
      // General mechanisms
      "Histologic transformation",
      "Bypass pathway activation",
      "Target mutation",
      "Loss of target expression",
    ],
  },

  // ============================================
  // CLINICAL CONTEXT (7 fields)
  // ============================================
  metastatic_site_1: {
    description: "Site of metastatic disease",
    allowedValues: [
      "Brain metastases",
      "Leptomeningeal disease",
      "Bone metastases",
      "Liver metastases",
      "Lung metastases",
      "Lymph node metastases",
      "Adrenal metastases",
      "Skin/soft tissue metastases",
      "Peritoneal metastases",
      "Pleural metastases",
      "CNS involvement",
    ],
  },

  metastatic_site_2: {
    description: "Secondary metastatic site",
    allowedValues: [], // Same values as metastatic_site_1
  },

  metastatic_site_3: {
    description: "Third metastatic site",
    allowedValues: [], // Same values as metastatic_site_1
  },

  symptom_1: {
    description: "Clinical symptom mentioned in vignette",
    allowedValues: [
      // Pain
      "Pain",
      "Bone pain",
      "Abdominal pain",
      "Chest pain",
      "Headache",
      "Back pain",
      // Constitutional
      "Fatigue",
      "Weight loss",
      "Night sweats",
      "Fever",
      "Anorexia",
      // Respiratory
      "Dyspnea",
      "Cough",
      "Hemoptysis",
      // GI
      "Nausea/vomiting",
      "Diarrhea",
      "Constipation",
      "Abdominal distension",
      // Neurologic
      "Peripheral neuropathy",
      "Cognitive changes",
      "Weakness",
      "Numbness/tingling",
      // Hematologic
      "Anemia symptoms",
      "Bleeding",
      "Infections",
      // Other
      "Edema",
      "Jaundice",
      "Skin changes",
    ],
  },

  symptom_2: {
    description: "Secondary symptom",
    allowedValues: [], // Same values as symptom_1
  },

  symptom_3: {
    description: "Third symptom",
    allowedValues: [], // Same values as symptom_1
  },

  performance_status: {
    description: "ECOG performance status (use fitness_status for Fit/Unfit/Frail)",
    allowedValues: ["ECOG 0", "ECOG 1", "ECOG 0-1", "ECOG 2", "ECOG 3-4"],
    note: "Only ECOG scores. For fitness categories (Fit/Unfit/Frail), use fitness_status field instead",
  },

  // ============================================
  // SAFETY & TOXICITY (7 fields)
  // ============================================
  toxicity_type_1: {
    description: "Specific toxicity/adverse event",
    allowedValues: [
      // Immune-related AEs
      "Immune-related colitis",
      "Immune-related hepatitis",
      "Immune-related pneumonitis",
      "Immune-related thyroiditis",
      "Immune-related hypophysitis",
      "Immune-related nephritis",
      "Immune-related myocarditis",
      "Immune-related dermatitis",
      // Hematologic toxicities
      "Neutropenia",
      "Febrile neutropenia",
      "Thrombocytopenia",
      "Anemia",
      "Pancytopenia",
      "Lymphopenia",
      // GI toxicities
      "Diarrhea",
      "Nausea/vomiting",
      "Mucositis",
      "Colitis",
      "Hepatotoxicity",
      // Pulmonary toxicities
      "Interstitial lung disease (ILD)",
      "Pneumonitis",
      // Cardiac toxicities
      "Cardiotoxicity",
      "QT prolongation",
      "Hypertension",
      "Heart failure",
      // Neurologic toxicities
      "Peripheral neuropathy",
      "Neurotoxicity",
      "ICANS",
      // CAR-T/bispecific toxicities
      "Cytokine release syndrome (CRS)",
      "Tumor lysis syndrome",
      "ICANS",
      // Dermatologic toxicities
      "Rash",
      "Hand-foot syndrome",
      "Alopecia",
      "Skin toxicity",
      // Metabolic toxicities
      "Hyperglycemia",
      "Electrolyte abnormalities",
      // Renal toxicities
      "Nephrotoxicity",
      "Acute kidney injury",
      // Infusion reactions
      "Infusion reaction",
      // Other
      "Fatigue",
      "Infections",
      "Bleeding",
      "Thromboembolic events",
    ],
  },

  toxicity_type_2: {
    description: "Secondary toxicity",
    allowedValues: [], // Same values as toxicity_type_1
  },

  toxicity_type_3: {
    description: "Third toxicity",
    allowedValues: [], // Same values as toxicity_type_1
  },

  toxicity_type_4: {
    description: "Fourth toxicity",
    allowedValues: [], // Same values as toxicity_type_1
  },

  toxicity_type_5: {
    description: "Fifth toxicity",
    allowedValues: [], // Same values as toxicity_type_1
  },

  toxicity_organ: {
    description: "Organ system affected by toxicity",
    allowedValues: [
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
    ],
  },

  toxicity_grade: {
    description: "CTCAE grade of toxicity",
    allowedValues: [
      "Grade 1",
      "Grade 2",
      "Grade 3",
      "Grade 4",
      "Grade 5",
      "Grade 1-2",
      "Grade >=3",
      "Any grade",
      "Serious",
      "Dose-limiting",
    ],
  },

  // ============================================
  // EFFICACY & OUTCOMES (5 fields)
  // ============================================
  efficacy_endpoint_1: {
    description: "Primary efficacy endpoint",
    allowedValues: [
      // Survival endpoints
      "Overall survival (OS)",
      "Progression-free survival (PFS)",
      "Disease-free survival (DFS)",
      "Event-free survival (EFS)",
      "Recurrence-free survival (RFS)",
      "Relapse-free survival",
      "Time to progression (TTP)",
      // Response endpoints
      "Overall response rate (ORR)",
      "Complete response rate (CR)",
      "Stringent complete response (sCR)",
      "Very good partial response (VGPR)",
      "Partial response (PR)",
      "Disease control rate (DCR)",
      "Duration of response (DoR)",
      // Pathologic endpoints
      "Pathologic complete response (pCR)",
      "Major pathologic response (MPR)",
      // Molecular endpoints
      "MRD negativity",
      "MRD-negative CR",
      "Molecular response",
      "ctDNA clearance",
      // Quality of life
      "Quality of life",
      "Patient-reported outcomes",
      "Time to deterioration",
    ],
  },

  efficacy_endpoint_2: {
    description: "Secondary efficacy endpoint",
    allowedValues: [], // Same values as efficacy_endpoint_1
  },

  efficacy_endpoint_3: {
    description: "Third efficacy endpoint",
    allowedValues: [], // Same values as efficacy_endpoint_1
  },

  outcome_context: {
    description: "Context of the efficacy data",
    allowedValues: [
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
    ],
  },

  clinical_benefit: {
    description: "Nature of clinical benefit",
    allowedValues: [
      "Statistically significant",
      "Clinically meaningful",
      "Non-inferior",
      "Superior",
      "Trend toward benefit",
      "No significant difference",
      "Hazard ratio",
      "Absolute benefit",
      "Relative risk reduction",
    ],
  },

  // ============================================
  // EVIDENCE & GUIDELINES (3 fields)
  // ============================================
  guideline_source_1: {
    description: "Guideline source if mentioned",
    allowedValues: [
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
      "Expert consensus",
    ],
  },

  guideline_source_2: {
    description: "Secondary guideline source",
    allowedValues: [], // Same values as guideline_source_1
  },

  evidence_type: {
    description: "Type of evidence discussed",
    allowedValues: [
      "Phase 3 RCT",
      "Phase 2 RCT",
      "Phase 1/2 trial",
      "Phase 1 trial",
      "Single-arm trial",
      "Real-world evidence",
      "Retrospective study",
      "Meta-analysis",
      "Systematic review",
      "Guideline recommendation",
    ],
  },

  // ============================================
  // QUESTION FORMAT & QUALITY (13 fields)
  // ============================================
  cme_outcome_level: {
    description: "Moore's level of CME outcome",
    allowedValues: ["3 - Knowledge", "4 - Competence", "5 - Performance"],
    note: "Level 3 = recall/recognition, Level 4 = application to clinical scenario",
  },

  data_response_type: {
    description: "Type of response the question elicits",
    allowedValues: ["Boolean", "Numeric", "Comparative", "Qualitative"],
    note: "Boolean = Yes/No or True/False. Numeric = specific number/statistic. Comparative = explicit comparison (most appropriate, best, preferred). Qualitative = identification/selection without comparative framing (What is your diagnosis?)",
  },

  stem_type: {
    description: "Format of the question stem",
    allowedValues: ["Clinical vignette", "Direct question", "Incomplete statement"],
    note: "Clinical vignette = patient case, Direct question = no patient context",
  },

  lead_in_type: {
    description: "Type of question lead-in",
    allowedValues: ["Standard", "Negative (EXCEPT/NOT)", "Best answer", "True statement"],
  },

  answer_format: {
    description: "Structure of answer options",
    allowedValues: ["Single best", "Compound (A+B)", "All of above", "None of above", "True-False"],
  },

  answer_length_pattern: {
    description: "Relative length of answer options",
    allowedValues: ["Uniform", "Variable", "Correct longest", "Correct shortest"],
    note: "Uniform = all ~same length. Variable = knowledge questions with 5-word vs 12-word statements. Correct longest/shortest = potential test-writing flaw",
  },

  distractor_homogeneity: {
    description: "Whether distractors are from the same conceptual category",
    allowedValues: ["Homogeneous", "Heterogeneous"],
    note: "Homogeneous = all from same category (e.g., all drugs). Heterogeneous = mixed categories (allows elimination)",
  },

  // Boolean flaw fields (read-only display)
  flaw_absolute_terms: {
    description: "Contains absolute terms (always, never, all, none)",
    note: "Boolean - computed by LLM. Test-wise examinees know absolutes are usually wrong",
  },

  flaw_grammatical_cue: {
    description: "Stem grammar reveals the answer",
    note: "Boolean - computed by LLM. Grammar matching guides to correct answer",
  },

  flaw_implausible_distractor: {
    description: "Contains obviously wrong options",
    note: "Boolean - computed by LLM. Reduces effective choices",
  },

  flaw_clang_association: {
    description: "Answer shares unusual words with stem",
    note: "Boolean - computed by LLM. Word repetition guides to answer",
  },

  flaw_convergence_vulnerability: {
    description: "Correct answer combines elements from multiple options",
    note: "Boolean - computed by LLM. Allows reasoning to answer without knowledge",
  },

  flaw_double_negative: {
    description: "Negative stem combined with negative option",
    note: "Boolean - computed by LLM. Increases cognitive load",
  },

  // ============================================
  // COMPUTED FIELDS (read-only)
  // ============================================
  answer_option_count: {
    description: "Number of answer options (2-5)",
    note: "Computed from raw data - not editable",
  },

  correct_answer_position: {
    description: "Position of correct answer (A, B, C, D, E)",
    note: "Computed from raw data - not editable",
  },
}

// Field groups for organizing the guidance modal
export const GUIDANCE_GROUPS = {
  core: {
    label: "Core Classification",
    fields: ["topic", "disease_state", "disease_stage", "disease_type_1", "disease_type_2", "treatment_line"],
  },
  multiValue: {
    label: "Treatments, Biomarkers & Trials",
    fields: [
      "treatment_1", "treatment_2", "treatment_3", "treatment_4", "treatment_5",
      "biomarker_1", "biomarker_2", "biomarker_3", "biomarker_4", "biomarker_5",
      "trial_1", "trial_2", "trial_3", "trial_4", "trial_5",
    ],
  },
  patientCharacteristics: {
    label: "Patient Characteristics",
    fields: ["treatment_eligibility", "age_group", "organ_dysfunction", "fitness_status", "disease_specific_factor", "comorbidity_1", "comorbidity_2", "comorbidity_3"],
  },
  treatmentDetails: {
    label: "Treatment Details",
    fields: [
      "drug_class_1", "drug_class_2", "drug_class_3",
      "drug_target_1", "drug_target_2", "drug_target_3",
      "prior_therapy_1", "prior_therapy_2", "prior_therapy_3",
      "resistance_mechanism",
    ],
  },
  clinicalContext: {
    label: "Clinical Context",
    fields: [
      "metastatic_site_1", "metastatic_site_2", "metastatic_site_3",
      "symptom_1", "symptom_2", "symptom_3",
      "performance_status",
    ],
  },
  safetyToxicity: {
    label: "Safety & Toxicity",
    fields: [
      "toxicity_type_1", "toxicity_type_2", "toxicity_type_3", "toxicity_type_4", "toxicity_type_5",
      "toxicity_organ", "toxicity_grade",
    ],
  },
  efficacyOutcomes: {
    label: "Efficacy & Outcomes",
    fields: ["efficacy_endpoint_1", "efficacy_endpoint_2", "efficacy_endpoint_3", "outcome_context", "clinical_benefit"],
  },
  evidenceGuidelines: {
    label: "Evidence & Guidelines",
    fields: ["guideline_source_1", "guideline_source_2", "evidence_type"],
  },
  questionQuality: {
    label: "Question Format & Quality",
    fields: [
      "cme_outcome_level", "data_response_type", "stem_type", "lead_in_type",
      "answer_format", "answer_length_pattern", "distractor_homogeneity",
      "flaw_absolute_terms", "flaw_grammatical_cue", "flaw_implausible_distractor",
      "flaw_clang_association", "flaw_convergence_vulnerability", "flaw_double_negative",
    ],
  },
  computed: {
    label: "Computed Fields (Read-only)",
    fields: ["answer_option_count", "correct_answer_position"],
  },
}
