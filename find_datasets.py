import copernicusmarine

print("Searching for global ocean colour chlorophyll products...")
result = copernicusmarine.describe(contains=["CHL"])

for product in result.products:
    pid = product.product_id
    # Only show global/multi ocean colour products
    if "OCEANCOLOUR" in pid or "BGC" in pid:
        print(f"\nProduct: {pid}")
        for dataset in product.datasets:
            print(f"  Dataset: {dataset.dataset_id}")