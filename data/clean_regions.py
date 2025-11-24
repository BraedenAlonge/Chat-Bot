import csv
import re

input_file = "countries of the world.csv"
output_file = "countries_clean.csv"

def clean_region(region):
    if not region:
        return ""

    region = region.strip().strip('"').strip()
    region = re.sub(r"\s+", " ", region)
    region = region.title()

    return region

def clean_decimal(value):
    if not value:
        return value

    value = value.strip().strip('"').strip()

    # If the field contains a comma AND digits around it, treat it as decimal
    if re.match(r"^\d+,\d+$", value):
        value = value.replace(",", ".")
        return value

    # If it looks like a decimal with trailing zeros e.g. "0,00"
    if re.match(r"^\d+,\d+$", value):
        value = value.replace(",", ".")

    return value


with open(input_file, encoding="utf-8") as infile, open(output_file, "w", newline="", encoding="utf-8") as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    header = next(reader)
    writer.writerow(header)

    for row in reader:
        # Clean Region field
        row[1] = clean_region(row[1])

        # Clean decimal commas in all remaining fields
        for i in range(2, len(row)):
            row[i] = clean_decimal(row[i])

        writer.writerow(row)

print("✅ Done! Decimal commas converted. Output:", output_file)