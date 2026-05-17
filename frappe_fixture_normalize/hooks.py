app_name = "frappe_fixture_normalize"
app_title = "Frappe Fixture Normalize"
app_publisher = "rtCamp"
app_description = "Stable, merge-safe fixture export and import for Frappe apps."
app_email = "frappe@rtcamp.com"
app_license = "MIT"

after_migrate = ["frappe_fixture_normalize.loader.import_split_fixtures"]
