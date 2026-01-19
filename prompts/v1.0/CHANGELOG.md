# Prompt Version Changelog

## v1.0 (2025-01-14)

Initial prompt version for V3 3-model voting system.

### Features
- Comprehensive system prompt with all 8 tag categories
- 10 canonical topic values aligned with CME outcomes tracking
- Standardized disease state names for solid tumors and hematologic malignancies
- Clear guidelines for disease stage, type, treatment line
- JSON output format for structured parsing

### Few-Shot Examples
- 5 diverse examples covering different cancer types and tag combinations
- Examples include NSCLC, breast cancer, colorectal cancer, multiple myeloma
- Coverage of different topics: treatment selection, clinical efficacy, biomarker testing, AE management

### Edge Cases
- Multi-cancer questions guidance
- Supportive care without specific cancer
- Drug class vs specific drug handling
- Trial inference from context

### Known Limitations
- May need refinement based on model disagreements
- Edge cases for rare cancers not fully covered
- Combination therapy formatting may vary
