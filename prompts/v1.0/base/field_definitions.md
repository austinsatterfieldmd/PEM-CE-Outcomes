# Field Definitions — Eye Care CE Outcomes Edition

You must assign values for all fields below. Use `null` for fields that are not applicable or cannot be determined.

## Value Selection Guidance

**Strict fields** (use ONLY the listed values):
- topic, condition_severity, treatment_modality, guideline_source, evidence_type, cme_outcome_level, data_response_type, stem_type, lead_in_type, answer_format, answer_length_pattern, distractor_homogeneity

**Open fields with common values** (prefer listed values, may use others if confident):
- condition_subtype, treatment_1-5, diagnostic_marker_1-5, trial_1-5, drug_class_1-3, drug_target_1-3, prior_therapy_1-3

---

## Core Classification (4 fields)

### 1. topic
**REQUIRED** - Every question must have exactly one topic. Never null.

These topic tags are derived from the Eye Care CME Outcomes Taxonomy:

| Topic | Use When... |
|-------|-------------|
| **Treatment sequencing / algorithms** | Choosing which therapy, step therapy, first-line vs advanced, switching strategies |
| **Clinical trial data** | Phase 2/3 results, pivotal trial endpoints, extension study findings |
| **Real-world evidence** | Practice-based outcomes, registry data, retrospective analyses |
| **Pathophysiology / Mechanism of action** | VEGF pathways, Ang/Tie2, complement cascade, meibomian gland biology, drug MOA |
| **Diagnosis / Screening / Imaging** | OCT, OCT-A, fundus autofluorescence, corneal sensitivity testing, biomarkers |
| **Differential diagnosis** | TED mimics, NK misdiagnosis, DED subtypes, disease staging |
| **Safety / Adverse events / Toxicity** | Ocular AEs from systemic therapy, injection complications, drug interactions |
| **Patient monitoring / Follow-up** | Treat-and-extend intervals, progression assessment, retreatment criteria |
| **Guideline recommendations** | AAO PPP, EGS, TFOS DEWS II, other society guidelines explicitly referenced |
| **Multidisciplinary / Collaborative care** | OD–MD co-management, retina referral pathways, oncology–ophthalmology coordination |
| **Health equity / Disparities** | Racial/ethnic disparities in DR/glaucoma, access to care barriers |
| **Patient education / Counseling** | Shared decision-making, treatment expectations, caregiver involvement |
| **Managed care / Payer considerations** | Step therapy, biosimilar formulary, prior authorization |

### 2. condition_severity
**OPTIONAL** - Severity, stage, or classification of the condition.

**AMD:**
- `"Early AMD"` — drusen, RPE changes
- `"Intermediate AMD"` — large drusen, pigmentary changes
- `"Late AMD — neovascular (wet)"` — CNV, fluid, hemorrhage
- `"Late AMD — geographic atrophy"` — atrophic lesions, GA
- `"Bilateral"`, `"Unilateral"`

**Diabetic Eye Disease:**
- `"Mild NPDR"`, `"Moderate NPDR"`, `"Severe NPDR"`, `"PDR"` — diabetic retinopathy severity
- `"Center-involving DME"`, `"Non-center-involving DME"`

**Glaucoma:**
- `"Mild"`, `"Moderate"`, `"Severe"` — visual field-based severity
- `"Suspect"` — elevated IOP or suspicious disc without confirmed damage
- `"Low-tension / Normal-tension"`

**DED:**
- `"Mild"`, `"Moderate"`, `"Severe"` — TFOS DEWS II severity grading

**NK:**
- `"Stage 1 (epithelial)"`, `"Stage 2 (persistent epithelial defect)"`, `"Stage 3 (corneal ulcer/perforation)"`

**TED:**
- `"Active (CAS ≥ 3)"`, `"Inactive (CAS < 3)"`
- `"Mild"`, `"Moderate-to-severe"`, `"Sight-threatening"`

`null` if not specified

### 3. condition_subtype
**OPTIONAL** - Specific subtype of the condition.

**AMD Subtypes:**
- `"Neovascular AMD (nAMD)"` / `"Wet AMD"`
- `"Geographic atrophy (GA)"`
- `"Dry AMD (non-GA)"`
- `"Polypoidal choroidal vasculopathy (PCV)"`

**Diabetic Eye Disease Subtypes:**
- `"DME"` — diabetic macular edema
- `"Diabetic retinopathy (DR)"` — focus on retinopathy progression
- `"Diabetic retinal vascular disease"`

**Glaucoma Subtypes:**
- `"Primary open-angle (POAG)"`
- `"Angle-closure"`
- `"Normal-tension"`
- `"Pseudoexfoliative"`
- `"Neovascular glaucoma"`

**DED Subtypes:**
- `"Aqueous-deficient"`
- `"Evaporative"`
- `"MGD-associated"`
- `"Sjögren syndrome-related"`
- `"Mixed mechanism"`

**Keratoconus Subtypes:**
- `"Progressive"`, `"Stable"`, `"Post-CXL"`

`null` if not specified

### 4. treatment_modality
**OPTIONAL** - The therapeutic modality category from the taxonomy.

**Valid values:**
- `"Anti-VEGF therapy"` — aflibercept, ranibizumab, faricimab, biosimilars, treat-and-extend
- `"Complement pathway inhibitors"` — pegcetacoplan, avacincaptad pegol (for GA)
- `"ROCK inhibitors"` — netarsudil, IOP-lowering via trabecular outflow
- `"Neurostimulation / Neuromodulation"` — intranasal stimulation, TRPM8, tear production
- `"Surgical / Interventional"` — MIGS, cataract surgery, CXL, intravitreal injections
- `"Topical pharmacotherapy"` — presbyopia drops, DED lubricants, anti-inflammatory agents
- `"Biologic / Targeted therapy"` — IGF-1R inhibitors (TED), cenegermin (NK), gene therapy (XLRP)
- `"Biosimilars"` — retinal disease biosimilars, interchangeability

`null` if not specified

---

## Multi-value Fields (15 fields)

### 5-9. treatment_1 through treatment_5
**OPTIONAL** - Specific treatments mentioned. Use generic names.

**Common treatments by condition:**

**AMD (nAMD):**
- `"aflibercept"` (Eylea), `"aflibercept 8 mg"` (Eylea HD)
- `"ranibizumab"` (Lucentis), `"faricimab"` (Vabysmo)
- `"brolucizumab"` (Beovu)
- Biosimilars: `"ranibizumab-nuna"` (Byooviz), `"ranibizumab-eqrn"` (Cimerli)

**AMD (GA):**
- `"pegcetacoplan"` (Syfovre), `"avacincaptad pegol"` (Izervay)

**DME:**
- `"aflibercept"`, `"faricimab"`, `"ranibizumab"`
- `"dexamethasone intravitreal implant"` (Ozurdex)
- `"fluocinolone acetonide implant"` (Iluvien)

**Glaucoma:**
- `"latanoprost"`, `"travoprost"`, `"tafluprost"`, `"latanoprostene bunod"` (Vyzulta)
- `"netarsudil"` (Rhopressa), `"netarsudil/latanoprost"` (Rocklatan)
- `"timolol"`, `"brimonidine"`, `"dorzolamide"`
- MIGS: `"iStent inject W"`, `"Hydrus Microstent"`, `"XEN gel stent"`, `"Omni"`, `"Kahook Dual Blade"`

**DED:**
- `"cyclosporine"` (Restasis, Cequa), `"lifitegrast"` (Xiidra)
- `"varenicline nasal spray"` (Tyrvaya), `"perfluorohexyloctane"` (Miebo)
- `"loteprednol"`, `"fluorometholone"`

**NK:**
- `"cenegermin"` (Oxervate)

**TED:**
- `"teprotumumab"` (Tepezza)

**Presbyopia:**
- `"pilocarpine"` (Vuity)

**Keratoconus:**
- `"corneal cross-linking (CXL)"` — Avedro/Photrexa system

**Ocular Toxicity:**
- Tag the CAUSATIVE agent: `"belantamab mafodotin"`, `"mirvetuximab soravtansine"`, `"tisotumab vedotin"`

### 10-14. diagnostic_marker_1 through diagnostic_marker_5
**OPTIONAL** - Relevant diagnostic tests, imaging, or biomarkers.

**Common values:**
- Imaging: `"OCT"`, `"OCT-A"`, `"Fundus autofluorescence (FAF)"`, `"Fluorescein angiography (FA)"`, `"ICG angiography"`, `"Visual field testing"`, `"Corneal topography"`, `"Anterior segment OCT"`
- Tests: `"IOP measurement"`, `"Gonioscopy"`, `"Pachymetry"`, `"Corneal sensitivity (esthesiometry)"`, `"Schirmer test"`, `"TBUT"`, `"Meibography"`, `"MMP-9"`, `"Tear osmolarity"`
- Scores: `"CAS (Clinical Activity Score)"`, `"DEWS severity"`, `"ETDRS visual acuity"`, `"LogMAR"`, `"BCVA"`, `"PASI"` (for keratoconus)
- Labs: `"A1C"` (diabetic context), `"TSH/TRAb"` (TED context)

### 15-19. trial_1 through trial_5
**CONDITIONAL** — Tag when explicitly mentioned or inferable for "Clinical trial data" or "Real-world evidence" topics.

**Key eye care trials:**
- AMD (nAMD): `"PULSAR"`, `"TENAYA"`, `"LUCERNE"`, `"HARBOR"`, `"VIEW 1/2"`, `"HAWK/HARRIER"`, `"CANDELA"`
- AMD (GA): `"OAKS"`, `"DERBY"`, `"GATHER1"`, `"GATHER2"`
- DME: `"YOSEMITE"`, `"RHINE"`, `"PANORAMA"`, `"VIVID/VISTA"`, `"Protocol T"`, `"Protocol V"`
- Glaucoma: `"LiGHT"`, `"COMPASS"`, `"HORIZON"`
- DED: `"ONSET-1/2"`, `"BREEZE"`, `"MOJAVE"`
- TED: `"OPTIC"`, `"OPTIC-J"`
- NK: `"REPARO"`, `"NGF0214"`
- Keratoconus: `"CXL-USA"`

---

## Group A: Treatment Metadata (7 fields)

### 20-22. drug_class_1 through drug_class_3
**Common values:**
`"Anti-VEGF"`, `"Complement C3 inhibitor"`, `"Complement C5 inhibitor"`, `"ROCK inhibitor"`, `"Prostaglandin analog"`, `"Beta-blocker (ophthalmic)"`, `"Alpha-agonist"`, `"Carbonic anhydrase inhibitor"`, `"Calcineurin inhibitor (ophthalmic)"`, `"LFA-1 antagonist"`, `"IGF-1R inhibitor"`, `"Recombinant NGF"`, `"Intravitreal corticosteroid"`, `"Bispecific antibody (ophthalmic)"`, `"Gene therapy"`, `"Cholinergic agonist"`, `"Anti-VEGF biosimilar"`, `"TRPM8 agonist"`, `"Tear film stabilizer"`, `"Anti-inflammatory (topical)"`

### 23-25. drug_target_1 through drug_target_3
**Common values:**
`"VEGF-A"`, `"VEGF-A + Ang-2"` (faricimab), `"Complement C3"`, `"Complement C5"`, `"Rho kinase"`, `"Prostaglandin F2α receptor"`, `"IGF-1R"`, `"NGF/TrkA"`, `"Muscarinic receptor"`, `"LFA-1/ICAM-1"`, `"Calcineurin"`, `"TRPM8"`

### 26-28. prior_therapy_1 through prior_therapy_3
**OPTIONAL** - Prior treatments mentioned.

Examples: `"Prior anti-VEGF"`, `"Prior ranibizumab"`, `"Prior prostaglandin"`, `"Failed topical cyclosporine"`, `"Prior cataract surgery"`

---

## Group B: Clinical Context (8 fields)

### 29-31. comorbidity_1 through comorbidity_3
**OPTIONAL** - Systemic or ocular comorbidities.

Examples: `"Diabetes mellitus"`, `"Hypertension"`, `"Thyroid disease"`, `"Sjögren syndrome"`, `"Autoimmune disease"`, `"Pseudophakia"`, `"Previous retinal detachment"`, `"Kidney disease"`

### 32-34. symptom_1 through symptom_3
**OPTIONAL** - Clinical symptoms mentioned.

Examples: `"Vision loss"`, `"Blurred vision"`, `"Floaters"`, `"Eye pain"`, `"Dry eye symptoms"`, `"Foreign body sensation"`, `"Photophobia"`, `"Proptosis"`, `"Diplopia"`, `"Tearing"`, `"Redness"`, `"Metamorphopsia"`

### 35-36. special_population_1 through special_population_2
**Valid values:**
`"Pediatric"`, `"Elderly (≥65)"`, `"Elderly (≥75)"`, `"Pregnant"`, `"Pseudophakic"`, `"Phakic"`, `"Monocular"`, `"Military/aviation"`, `"Cancer patient"`, `"Autoimmune disease"`, `"Post-refractive surgery"`

---

## Group C: Safety/Toxicity (7 fields)

### 37-41. toxicity_type_1 through toxicity_type_5
**Common values:**
- Injection-related: `"Endophthalmitis"`, `"Retinal detachment"`, `"Intraocular inflammation"`, `"IOP spike"`, `"Vitreous hemorrhage"`, `"Retinal vasculitis"`
- Topical: `"Hyperemia"`, `"Ocular surface toxicity"`, `"Periocular skin changes"`, `"Iris pigmentation"`, `"Corneal epitheliopathy"`
- Systemic drug ocular AEs: `"Corneal epithelial changes"`, `"Dry eye"`, `"Blurred vision"`, `"Keratopathy"`, `"Uveitis"`, `"Retinal toxicity"`
- Surgical: `"Cystoid macular edema (Irvine-Gass)"`, `"Posterior capsule opacification"`, `"IOL dislocation"`, `"Hypotony"`

### 42. toxicity_organ
**Valid values:** `"Cornea"`, `"Retina"`, `"Optic nerve"`, `"Lens"`, `"Uvea"`, `"Conjunctiva"`, `"Eyelid"`, `"Orbit"`, `"Lacrimal system"`, `"Anterior chamber"`, `"Vitreous"`

### 43. toxicity_grade
**Valid values:** `"Mild"`, `"Moderate"`, `"Severe"`, `"Sight-threatening"`, `"Any grade"`, `"Grade 1"`, `"Grade 2"`, `"Grade 3"`, `"Grade ≥3"`

---

## Group D: Efficacy/Outcomes (5 fields)

### 44-46. efficacy_endpoint_1 through efficacy_endpoint_3
**CONDITIONAL** — Tag ONLY for "Clinical trial data" or "Real-world evidence" topics.

**Common values:**
- Visual acuity: `"BCVA change from baseline"`, `"BCVA letter gain"`, `"Proportion gaining ≥15 letters"`, `"Proportion losing <15 letters"`
- Anatomic: `"CST change (central subfield thickness)"`, `"GA lesion growth rate"`, `"Retinal fluid resolution"`, `"Drusen volume"`, `"Foveal avascular zone"`
- Glaucoma: `"IOP reduction"`, `"IOP ≤18 mmHg"`, `"Visual field progression"`, `"RNFL thickness change"`
- DED: `"Schirmer score"`, `"TBUT"`, `"Corneal staining score"`, `"OSDI score"`, `"Symptom score"`
- Treatment burden: `"Injection frequency"`, `"Treatment interval"`, `"Time to retreatment"`
- TED: `"Proptosis reduction"`, `"Diplopia response"`, `"CAS change"`

### 47. outcome_context
**Valid values:** `"Primary endpoint met"`, `"Primary endpoint not met"`, `"Secondary endpoint"`, `"Exploratory endpoint"`, `"Subgroup analysis"`, `"Post-hoc analysis"`, `"Interim analysis"`, `"Final analysis"`, `"Extension study"`, `"Real-world data"`

### 48. clinical_benefit
**Valid values:** `"Statistically significant"`, `"Clinically meaningful"`, `"Non-inferior"`, `"Superior"`, `"Trend toward benefit"`, `"No significant difference"`

---

## Group E: Evidence/Guidelines (3 fields)

### 49-50. guideline_source_1 through guideline_source_2
**CONDITIONAL** - Tag ONLY when explicitly named.

**Valid values:**
`"AAO PPP"` (American Academy of Ophthalmology Preferred Practice Pattern), `"EGS"` (European Glaucoma Society), `"TFOS DEWS II"` (Tear Film & Ocular Surface Society), `"ICO"` (International Council of Ophthalmology), `"EURETINA"`, `"ASRS"`, `"WGA"` (World Glaucoma Association), `"FDA label"`, `"Expert consensus"`, `"ADA"` (for diabetic eye screening), `"AOA"` (American Optometric Association)

### 51. evidence_type
**Valid values:** `"Phase 3 RCT"`, `"Phase 2 RCT"`, `"Phase 1/2 trial"`, `"Single-arm trial"`, `"Real-world evidence"`, `"Retrospective study"`, `"Meta-analysis"`, `"Registry data"`, `"Guideline recommendation"`, `"Expert consensus"`, `"Extension study"`

---

## Group F: Question Format/Quality (13 fields)

### 52. cme_outcome_level
- `"3 - Knowledge"` — recall/recognition
- `"4 - Competence"` — application to clinical scenario

### 53. data_response_type
`"Numeric"`, `"Qualitative"`, `"Comparative"`, `"Boolean"`

### 54. stem_type
`"Clinical vignette"`, `"Direct question"`, `"Incomplete statement"`

### 55. lead_in_type
`"Standard"`, `"Negative (EXCEPT/NOT)"`, `"Best answer"`, `"True statement"`

### 56. answer_format
`"Single best"`, `"Compound (A+B)"`, `"All of above"`, `"None of above"`, `"True-False"`

### 57. answer_length_pattern
**DEFAULT: "Uniform"**
`"Uniform"`, `"Variable"`, `"Correct longest"`, `"Correct shortest"`

### 58. distractor_homogeneity
`"Homogeneous"`, `"Heterogeneous"`

### Item Writing Flaws (59-64) — Boolean (true/false)
### 59. flaw_absolute_terms
### 60. flaw_grammatical_cue
### 61. flaw_implausible_distractor
### 62. flaw_clang_association
### 63. flaw_convergence_vulnerability
### 64. flaw_double_negative

---

## Program Format Metadata (2 fields — NEW, not in oncology schema)

### 65. program_format
**OPTIONAL** - Format of the CE program this question appeared in.

**Valid values:**
`"Live (in-person)"`, `"Virtual / Online"`, `"Hybrid"`, `"Micro-learning"`

### 66. credit_type
**OPTIONAL** - Type of CE credit.

**Valid values:**
`"CME (ACCME)"`, `"COPE"`, `"CNE (nursing)"`, `"Pharmacist CE"`, `"Joint-accredited"`