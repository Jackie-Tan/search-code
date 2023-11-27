import pandas as pd

df = pd.read_csv("final_data_v2.csv")

# Group by 'repo_base_url' and aggregate 'repo_patch_url' into lists
aggregated_data = df.groupby('repo_base_url')['repo_patch_url'].agg(list).reset_index()

# Rename 'repo_patch_url' column to 'repo_patch_urls'
aggregated_data = aggregated_data.rename(columns={'repo_patch_url': 'repo_patch_urls'})

# Remove duplicate URLs within each list in the 'repo_patch_urls' column
aggregated_data['repo_patch_urls'] = aggregated_data['repo_patch_urls'].apply(lambda urls: list(set(urls)))

output_file_path = 'final_data_v3.csv'
aggregated_data.to_csv(output_file_path, index=False)