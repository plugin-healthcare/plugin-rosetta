# Errors and Reports

Package-wide exceptions and the validation report returned by mapping and vocabulary checks.
Import these names from `plugin_rosetta`.
Almost every exception raised on purpose by Rosetta derives from `RosettaError`, so a caller can usually catch that one class.
The exception is an invalid selector argument in the vocabulary API, such as an unknown DHD thesaurus or an unregistered source name, which raises a plain `ValueError`.

## Validation reports

::: plugin_rosetta.reports
    options:
      show_root_heading: false
      show_root_toc_entry: false
      heading_level: 3

## Errors

::: plugin_rosetta.errors
    options:
      show_root_heading: false
      show_root_toc_entry: false
      heading_level: 3
