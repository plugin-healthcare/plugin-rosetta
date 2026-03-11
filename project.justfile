## Project-specific just recipes for plugin-rosetta.
## This file is imported by the main justfile.

# Pinned upstream source versions
omop_cdm_tag := "v5.4.2"
fhir_omop_ig_tag := "1.0.0-ballot"
nyctea_commit := "6b113f17c2d9fd578e56ca8c89555ac9a71f7130"

omop_base_url := "https://raw.githubusercontent.com/OHDSI/CommonDataModel/" + omop_cdm_tag + "/inst/csv"
fhir_omop_base_url := "https://raw.githubusercontent.com/HL7/fhir-omop-ig/" + fhir_omop_ig_tag + "/input/maps"

# Install nyctea separately (its pyproject.toml has an erroneous requires-python >= 3.14)
[group('project management')]
install-nyctea:
    uv pip install --no-deps "nyctea @ git+https://github.com/yannick-vinkesteijn/nyctea.git@{{nyctea_commit}}"

# Download upstream source files (OHDSI OMOP CSVs + HL7 FHIR-OMOP FML maps)
[group('schema generation')]
download-sources:
    mkdir -p sources/omop sources/fhir-omop-ig/maps
    curl -fsSL -o sources/omop/OMOP_CDMv5.4_Field_Level.csv \
        "{{omop_base_url}}/OMOP_CDMv5.4_Field_Level.csv"
    curl -fsSL -o sources/omop/OMOP_CDMv5.4_Table_Level.csv \
        "{{omop_base_url}}/OMOP_CDMv5.4_Table_Level.csv"
    @echo "Downloading FHIR-OMOP IG mapping files (tag: {{fhir_omop_ig_tag}})..."
    @for f in PersonMap EncounterVisit condition Measurement Observation Procedure medication ImmunizationMap Allergy; do \
        echo "  -> $f.fml"; \
        curl -fsSL -o "sources/fhir-omop-ig/maps/$f.fml" \
            "{{fhir_omop_base_url}}/$f.fml"; \
    done
    @echo "Sources downloaded."

# Generate the OMOP CDM LinkML schemas from OHDSI CSV files
[group('schema generation')]
gen-omop-schema: download-sources
    uv run --no-sync python -m plugin_rosetta.generate_omop_schema

# Enrich FHIR schema slots with exact_mappings from FHIR-OMOP IG FML files
[group('schema generation')]
gen-mappings: download-sources
    uv run --no-sync python -m plugin_rosetta.parse_fml_mappings

# Generate Pydantic v2 models from all LinkML schemas (merged single file)
[group('schema generation')]
gen-pydantic:
    uv run --no-sync gen-pydantic \
        --extra-fields ignore \
        src/plugin_rosetta/schema/plugin_rosetta.yaml \
        2>/dev/null > src/plugin_rosetta/datamodel/plugin_rosetta_pydantic.py

# Full schema regeneration pipeline: OMOP CSV -> LinkML -> mappings -> Pydantic
[group('schema generation')]
gen-all: gen-omop-schema gen-mappings gen-pydantic gen-project

# Validate an OMOP-structured Parquet file against the nyctea schema for a given table
[group('validation')]
validate-omop-parquet path table:
    uv run --no-sync python src/plugin_rosetta/validate_omop.py "{{path}}" "{{table}}"

# Run documentation dev server with zensical
# NOTE: to override the main justfile's _serve, add this to the bottom of justfile
[group('documentation')]
zensical-serve:
    uv run --no-sync zensical serve

# Build and deploy documentation to GitHub Pages with zensical
# NOTE: to override the main justfile's deploy, add this to the bottom of justfile
[group('documentation')]
zensical-deploy:
    uv run --no-sync zensical gh-deploy
