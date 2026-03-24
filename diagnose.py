import joblib, pandas as pd, numpy as np, json
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

root = Path('.')
rec_scaler    = joblib.load(root/'models'/'rec_scaler.pkl')
centroids     = joblib.load(root/'models'/'centroids.pkl')
cluster_means = joblib.load(root/'models'/'cluster_product_means.pkl')
scaler        = joblib.load(root/'models'/'scaler.pkl')
pca           = joblib.load(root/'models'/'pca.pkl')
kmeans        = joblib.load(root/'models'/'kmeans.pkl')

cols = list(rec_scaler.feature_names_in_)
product_cols = ['Wines','Fruits','Meat','Fish','Sweets','Gold']
feature_cols = [c for c in cols if c not in product_cols]

# Load raw data
raw = pd.read_csv(root/'data'/'customer_segmentation_data.csv')
rename_map = {'MntWines':'Wines','MntFruits':'Fruits','MntMeatProducts':'Meat',
              'MntFishProducts':'Fish','MntSweetProducts':'Sweets','MntGoldProds':'Gold'}
raw = raw.rename(columns=rename_map)

# Real data stats
real_stats = {}
if all(c in raw.columns for c in feature_cols):
    desc = raw[feature_cols].describe().round(2)
    real_stats = desc.to_dict()

# Simulate user input from screenshot
user_data = {
  'Education':2,'Income':43000,'Kidhome':2,'Teenhome':1,
  'Recency':4,'Wines':340,'Fruits':65,'Meat':53,
  'Fish':34,'Sweets':65,'Gold':1094,
  'NumDealsPurchases':0,'NumWebPurchases':0,'NumCatalogPurchases':1,
  'NumStorePurchases':2,'NumWebVisitsMonth':0,
  'Customer_For':543,'Age':23,'Spent':8957,
  'Living_With':2,'Children':3,'Family_Size':5,'Is_Parent':1
}

user_df = pd.DataFrame([{k: user_data[k] for k in cols}])
user_scaled = pd.DataFrame(rec_scaler.transform(user_df), columns=cols)

# Similarity to each centroid
sims_to_centroids = {}
for cl in centroids.index:
    c_f = centroids.loc[cl, feature_cols].values.reshape(1,-1)
    u_f = user_scaled[feature_cols].values
    sim = float(cosine_similarity(u_f, c_f)[0][0])
    sims_to_centroids[int(cl)] = round(sim, 6)

# Predict cluster for this user
scaled_in = scaler.transform(user_df)
pca_in    = pca.transform(scaled_in)
predicted_cluster = int(kmeans.predict(pca_in)[0])

# Sample real customers similarity
real_sims = {}
if 'Clusters' in raw.columns:
    rec_all = raw[['Clusters'] + cols].copy()
    rec_all[cols] = rec_scaler.transform(rec_all[cols])
    for cl in sorted(raw['Clusters'].unique()):
        subset = rec_all[rec_all['Clusters']==cl].head(10)
        sims = []
        c_f = centroids.loc[cl, feature_cols].values.reshape(1,-1)
        for _, row in subset.iterrows():
            u_f = row[feature_cols].values.reshape(1,-1)
            sims.append(round(float(cosine_similarity(u_f, c_f)[0][0]), 4))
        real_sims[int(cl)] = {'count': int((raw['Clusters']==cl).sum()), 'sample_sims': sims}

result = {
    'feature_cols': feature_cols,
    'product_cols_for_recommendation': product_cols,
    'n_clusters': int(kmeans.n_clusters),
    'cluster_product_means': cluster_means.round(2).to_dict(),
    'user_input_similarity_to_each_centroid': sims_to_centroids,
    'user_predicted_cluster': predicted_cluster,
    'real_customer_sample_similarities': real_sims,
    'real_data_feature_stats': {k: {kk: float(vv) for kk,vv in v.items()} for k,v in real_stats.items()},
}
with open('diagnose_out.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print("DONE")
