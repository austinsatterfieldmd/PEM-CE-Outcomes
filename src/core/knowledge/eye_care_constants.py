"""
Constants for eye care conditions, treatments, abbreviations, and tag values.
PEM Eye Care CE Outcomes Dashboard — Core domain knowledge.
Derived from: Eye Care CME Outcomes Database Taxonomy Framework
"""

# =============================================================================
# CONDITIONS (from taxonomy Part 1: Disease State/Condition)
# =============================================================================

RETINAL_CONDITIONS = [
    "AMD",                          # Age-related macular degeneration
    "Diabetic eye disease",         # DME, DR, diabetic retinal vascular disease
    "Retinitis pigmentosa",         # XLRP, gene therapy, inherited retinal diseases
    "Macular telangiectasia",       # MacTel
    "Uveitic macular edema",       # UME
    "Retinal vein occlusion",       # RVO
]

GLAUCOMA_CONDITIONS = [
    "Glaucoma",                     # Open-angle, angle-closure, interventional/surgical
]

ANTERIOR_SEGMENT_CONDITIONS = [
    "Dry eye disease",              # DED: aqueous-deficient, evaporative, MGD, Sjögren
    "Neurotrophic keratitis",       # NK: staging, corneal sensitivity
    "Keratoconus",                  # Cross-linking, progression
    "Allergic conjunctivitis",      # Patient-centered treatment
    "Ocular surface disease",       # OSD: preservative impact, tear film
]

EYELID_ADNEXA_CONDITIONS = [
    "Blepharitis",                  # Demodex, blepharoptosis, lid disorders
    "Thyroid eye disease",          # TED: teprotumumab, collaborative care
]

SURGICAL_REFRACTIVE_CONDITIONS = [
    "Cataract / Refractive surgery",  # IOL selection, toric, complications
    "Presbyopia",                      # Pharmacological drops, accommodative loss
]

CROSS_DISCIPLINE_CONDITIONS = [
    "Ocular toxicity from cancer therapy",  # ADC-related, checkpoint inhibitor, multidisciplinary
]

ALL_CONDITIONS = (
    RETINAL_CONDITIONS
    + GLAUCOMA_CONDITIONS
    + ANTERIOR_SEGMENT_CONDITIONS
    + EYELID_ADNEXA_CONDITIONS
    + SURGICAL_REFRACTIVE_CONDITIONS
    + CROSS_DISCIPLINE_CONDITIONS
)

# =============================================================================
# CONDITION ABBREVIATION MAPPINGS
# =============================================================================
CONDITION_ABBREVIATIONS = {
    # AMD
    "nAMD": "AMD",
    "wet AMD": "AMD",
    "dry AMD": "AMD",
    "GA": "AMD",
    "geographic atrophy": "AMD",
    "neovascular AMD": "AMD",
    "age-related macular degeneration": "AMD",
    "CNV": "AMD",
    "PCV": "AMD",
    "polypoidal choroidal vasculopathy": "AMD",

    # Diabetic eye disease
    "DME": "Diabetic eye disease",
    "diabetic macular edema": "Diabetic eye disease",
    "DR": "Diabetic eye disease",
    "diabetic retinopathy": "Diabetic eye disease",
    "NPDR": "Diabetic eye disease",
    "PDR": "Diabetic eye disease",
    "proliferative diabetic retinopathy": "Diabetic eye disease",
    "non-proliferative diabetic retinopathy": "Diabetic eye disease",
    "CSME": "Diabetic eye disease",

    # Glaucoma
    "POAG": "Glaucoma",
    "primary open-angle glaucoma": "Glaucoma",
    "open-angle glaucoma": "Glaucoma",
    "OAG": "Glaucoma",
    "angle-closure glaucoma": "Glaucoma",
    "ACG": "Glaucoma",
    "NTG": "Glaucoma",
    "normal-tension glaucoma": "Glaucoma",
    "OHT": "Glaucoma",
    "ocular hypertension": "Glaucoma",

    # DED
    "DED": "Dry eye disease",
    "dry eye": "Dry eye disease",
    "MGD": "Dry eye disease",
    "meibomian gland dysfunction": "Dry eye disease",
    "KCS": "Dry eye disease",
    "keratoconjunctivitis sicca": "Dry eye disease",

    # NK
    "NK": "Neurotrophic keratitis",

    # TED
    "TED": "Thyroid eye disease",
    "Graves ophthalmopathy": "Thyroid eye disease",
    "Graves' ophthalmopathy": "Thyroid eye disease",
    "thyroid-associated orbitopathy": "Thyroid eye disease",
    "TAO": "Thyroid eye disease",

    # UME
    "UME": "Uveitic macular edema",

    # MacTel
    "MacTel": "Macular telangiectasia",
    "MacTel type 2": "Macular telangiectasia",

    # XLRP
    "XLRP": "Retinitis pigmentosa",
    "X-linked retinitis pigmentosa": "Retinitis pigmentosa",
    "RP": "Retinitis pigmentosa",
    "IRD": "Retinitis pigmentosa",
    "inherited retinal disease": "Retinitis pigmentosa",

    # RVO
    "RVO": "Retinal vein occlusion",
    "BRVO": "Retinal vein occlusion",
    "CRVO": "Retinal vein occlusion",
    "branch retinal vein occlusion": "Retinal vein occlusion",
    "central retinal vein occlusion": "Retinal vein occlusion",

    # OSD
    "OSD": "Ocular surface disease",

    # Surgical
    "IOL": "Cataract / Refractive surgery",
    "MIGS": "Glaucoma",  # MIGS procedures are glaucoma
    "CXL": "Keratoconus",
    "corneal cross-linking": "Keratoconus",
}

# =============================================================================
# TREATMENT MODALITIES (from taxonomy Part 1: Treatment Modality)
# =============================================================================
TREATMENT_MODALITIES = [
    "Anti-VEGF therapy",
    "Complement pathway inhibitors",
    "ROCK inhibitors",
    "Neurostimulation / Neuromodulation",
    "Surgical / Interventional",
    "Topical pharmacotherapy",
    "Biologic / Targeted therapy",
    "Biosimilars",
]

# =============================================================================
# TOPIC TAGS (from taxonomy Part 1: Clinical Knowledge Domain + Practice & Access)
# =============================================================================
TOPIC_TAGS = [
    "Treatment sequencing / algorithms",
    "Clinical trial data",
    "Real-world evidence",
    "Pathophysiology / Mechanism of action",
    "Diagnosis / Screening / Imaging",
    "Differential diagnosis",
    "Safety / Adverse events / Toxicity",
    "Patient monitoring / Follow-up",
    "Guideline recommendations",
    "Multidisciplinary / Collaborative care",
    "Health equity / Disparities",
    "Patient education / Counseling",
    "Managed care / Payer considerations",
]

# =============================================================================
# TREATMENT → CONDITION INFERENCE
# Drug-specific inference when condition is ambiguous
# =============================================================================
TREATMENT_TO_CONDITION = {
    # GA-specific
    "pegcetacoplan": "AMD",
    "avacincaptad pegol": "AMD",

    # TED-specific
    "teprotumumab": "Thyroid eye disease",

    # NK-specific
    "cenegermin": "Neurotrophic keratitis",

    # Glaucoma-specific
    "netarsudil": "Glaucoma",
    "latanoprostene bunod": "Glaucoma",

    # Presbyopia-specific
    "pilocarpine": "Presbyopia",  # Vuity context

    # DED-specific
    "lifitegrast": "Dry eye disease",
    "varenicline nasal spray": "Dry eye disease",
    "perfluorohexyloctane": "Dry eye disease",

    # Oncology drugs causing ocular toxicity
    "belantamab mafodotin": "Ocular toxicity from cancer therapy",
    "mirvetuximab soravtansine": "Ocular toxicity from cancer therapy",
    "tisotumab vedotin": "Ocular toxicity from cancer therapy",
}

# Ambiguous drugs that need context to disambiguate
AMBIGUOUS_TREATMENTS = {
    "aflibercept": ["AMD", "Diabetic eye disease", "Retinal vein occlusion"],
    "ranibizumab": ["AMD", "Diabetic eye disease", "Retinal vein occlusion"],
    "faricimab": ["AMD", "Diabetic eye disease"],
    "brolucizumab": ["AMD"],
    "cyclosporine": ["Dry eye disease"],  # Ophthalmic context
    "dexamethasone intravitreal implant": ["Diabetic eye disease", "Uveitic macular edema", "Retinal vein occlusion"],
}

# =============================================================================
# PROVIDER TYPES (from taxonomy Part 2: Learner Demographic Factors)
# =============================================================================
PROVIDER_TYPES = [
    "Optometrist (OD)",
    "Ophthalmologist (MD/DO)",
    "Retina Specialist",
    "Glaucoma Specialist",
    "Cornea / External Disease Specialist",
    "Cataract / Refractive Surgeon",
    "Oculoplastics Specialist",
    "Oncologist (Medical/Surgical)",
    "Nurse / NP / PA",
    "Pharmacist",
]

# =============================================================================
# GUIDELINE SOURCES
# =============================================================================
GUIDELINE_SOURCES = [
    "AAO PPP",       # American Academy of Ophthalmology Preferred Practice Pattern
    "EGS",           # European Glaucoma Society
    "TFOS DEWS II",  # Tear Film & Ocular Surface Society
    "ICO",           # International Council of Ophthalmology
    "EURETINA",
    "ASRS",
    "WGA",           # World Glaucoma Association
    "FDA label",
    "Expert consensus",
    "ADA",           # For diabetic eye screening
    "AOA",           # American Optometric Association
]

# =============================================================================
# CONFERENCE / ACTIVITY AFFILIATIONS (from taxonomy Part 2)
# =============================================================================
CONFERENCE_AFFILIATIONS = [
    "AAO",       # American Academy of Ophthalmology
    "AAOpt",     # American Academy of Optometry
    "ARVO",      # Association for Research in Vision and Ophthalmology
    "ASCRS",     # American Society of Cataract and Refractive Surgery
    "ASRS",      # American Society of Retina Specialists
    "EyeCon",
    "IKA",       # International Keratoconus Academy
    "CRU Symposium",
    "EnVision Summit",
]

# =============================================================================
# PROGRAM FORMATS (from taxonomy Part 1: Program Format)
# =============================================================================
PROGRAM_FORMATS = [
    "Live (in-person)",
    "Virtual / Online",
    "Hybrid",
    "Micro-learning",
]

# =============================================================================
# CREDIT TYPES (from taxonomy Part 2)
# =============================================================================
CREDIT_TYPES = [
    "CME (ACCME)",
    "COPE",
    "CNE (nursing)",
    "Pharmacist CE",
    "Joint-accredited",
]
