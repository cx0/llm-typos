import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

scenario = "scenario_1"
df_accuracies = pd.read_csv(f"experiments/{scenario}_accuracies.csv", header=0)

# Plot the retrieval accuracy by model and misspelling context
plt.figure(figsize=(16,14))
sns.set(font_scale=1.8)
sns.barplot(data=df_accuracies, x='model', y='accuracy', hue='condition')

plt.title('Retrieval accuracy by model and misspelling context\n', fontsize=24)
plt.ylabel('Accuracy\n')
plt.xlabel('')
plt.legend(title='Query word - Target sample text')


plt.tight_layout()
plt.savefig(f"figures/{scenario}_accuracies.png", dpi=300)

# Plot the retrieval accuracy for the preceding and following words
model = "Opus"
df_subset = df_accuracies[df_accuracies['model'] == model].reset_index()

df_long = df_subset.melt(id_vars="condition", value_vars=["pre_hit", "post_hit"], var_name="Phase", value_name="Accuracy")
phase_dict = {"pre_hit": "Preceding word",
              "post_hit": "Following word"}

df_long['Phase'] = df_long['Phase'].map(phase_dict)

plt.figure(figsize=(12,8))
sns.barplot(data=df_long, x='condition', y='Accuracy', hue='Phase', width=0.5)

plt.title('Opus predictive accuracy for preceding and following words by misspelling context\n\n\n')
plt.xlabel('\nQuery word - Target sample')
plt.ylabel('Accuracy\n')
plt.legend(title='', ncol=2, bbox_to_anchor=(0.5, 1.12), loc='upper center')

plt.tight_layout()
plt.savefig(f"figures/{scenario}_accuracies_pre_vs_post.png", dpi=300)
