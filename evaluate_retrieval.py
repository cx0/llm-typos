import re
import anthropic
import pandas as pd

client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="your_api_key"
)

def extract_surrounding_words(df, target_word_col, target_piece_col, output_prefix=''):
    def find_surrounding_words(row):
        target_word = row[target_word_col]
        target_piece = row[target_piece_col]
        
        # Remove punctuation and convert to lowercase
        target_piece = re.sub(r'[^\w\s]', '', target_piece.lower())
        
        # Limit the retrieval to whole words
        words = target_piece.split()
        
        # Find the index of the target word and retrieve the neighbors
        try:
            index = words.index(target_word.lower())
            preceding_word = words[index - 1] if index > 0 else 'not_found'
            following_word = words[index + 1] if index < len(words) - 1 else 'not_found'
        except ValueError:
            preceding_word = 'not_found'
            following_word = 'not_found'
        
        return pd.Series([preceding_word, following_word])
    
    df[[output_prefix + 'preceding_word', output_prefix + 'following_word']] = df.apply(find_surrounding_words, axis=1)
    
    return df

# Note that the ground truth (acutal) preceding and following words are the same for the correctly spelled and misspelled words
scenario = "scenario_1"

df = pd.read_json(f"experiments/{scenario}.json")
df = extract_surrounding_words(df, 'correct_word', 'correct_sample_text', 'actual_')

# Make an API call to the respective model (see README for details on system and user prompts)
# Note: Play around with the prompt length and maximum tokens if you run into rate limits
def generate_response(model: str, word: str, sample_text: str) -> str:
    message = client.messages.create(
        model=model,
        max_tokens=1000,
        temperature=0,
        system="You assist users to search long text documents that may or may not contain common misspellings in English. \n\n- User provides two inputs: TARGET_WORD and TARGET_SAMPLE. \n- Please find the single words that immediately precede and follow the word TARGET_WORD, respectively in TARGET_SAMPLE. \n- Ignore case, whitespace and punctuation when searching for TARGET_WORD, only consider whole words. \n- If you autocorrect any misspelled words in TARGET_WORD or TARGET_SAMPLE, mention each misspelled word and your corrected version inside <misspelled> and <corrected> tags in your response before returning the <preceding> and <following> tags. \n- Return your response in the following format:\n<misspelled>misspelled_word</misspelled><corrected>corrected_word</corrected>\n\n<preceding>preceding_word</preceding><following>following_word</following>\n\n- If you do not make any spelling corrections, omit the <misspelled> and <corrected> tags. \n- If you are confident that the TARGET_SAMPLE does not contain TARGET_WORD or their common misspelling, then use \"NOT_FOUND\" inside the <preceding> and <following> tags. \n- Be concise and only include the requested words in the specified format in the response, nothing else.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "TARGET_WORD: \"" + word + "\"\nTARGET_SAMPLE: \"" + sample_text + "\""
                    }
                ]
            }
        ]
    )

    return message.content[0].text


def search_and_update(df: pd.DataFrame, model: str, alias: str, query_word_column: str, query_sample_column: str):
    def process_row(row):
        target_word = row[query_word_column]
        target_sample = row[query_sample_column]
        response = generate_response(model, target_word, target_sample)
        prefix = query_word_column[0].upper() + query_sample_column[0].upper()
        column_name = f"{alias}_{prefix}_response"
        return pd.Series({column_name: response})

    new_columns = df.apply(process_row, axis=1)
    return pd.concat([df, new_columns], axis=1)

def process_dataframe(df: pd.DataFrame, models: dict):
    word_sample_pairs = [
        ["correct_word", "correct_sample_text"], # CC
        ["correct_word", "misspelled_sample_text"], # CM
        ["misspelled_word", "correct_sample_text"], # MC
        ["misspelled_word", "misspelled_sample_text"] # MM
    ]

    for model, alias in models.items():
        for query_word_column, query_sample_column in word_sample_pairs:
            df = search_and_update(df, model, alias, query_word_column, query_sample_column)

    return df

models = {
    "claude-3-haiku-20240307": "haiku",
    "claude-3-sonnet-20240229": "sonnet",
    "claude-3-opus-20240229": "opus"
}

processed_df = process_dataframe(df, models)
processed_df.to_csv(f"experiments/{scenario}_results.csv", index=False, header=True) # save API call results

# Calculate the retrieval accuracy
model_response_cols = [
    ('haiku', ['haiku_CC_response', 'haiku_CM_response', 'haiku_MC_response', 'haiku_MM_response']),
    ('sonnet', ['sonnet_CC_response', 'sonnet_CM_response', 'sonnet_MC_response', 'sonnet_MM_response']),
    ('opus', ['opus_CC_response', 'opus_CM_response', 'opus_MC_response', 'opus_MM_response']),
]

accuracies = []
for model, cols in model_response_cols:
    for col in cols:
        condition = col.split('_')[-2] 
        print(model, condition)
        df[f'{model}_{condition}_preceding'] = df[f'{model}_{condition}_response'].str.extract(r'<preceding>(.*?)</preceding>', expand=False).str.lower()
        df[f'{model}_{condition}_following'] = df[f'{model}_{condition}_response'].str.extract(r'<following>(.*?)</following>', expand=False).str.lower()

        df['actual_preceding_word'] = df['actual_preceding_word'].str.lower()
        df['actual_following_word'] = df['actual_following_word'].str.lower()

        pre_hit = sum(df[f'{model}_{condition}_preceding']== df['actual_preceding_word'])
        post_hit = sum(df[f'{model}_{condition}_following'] == df['actual_following_word'])
        print(f'Preceding Hits: {pre_hit}, Post Hits: {post_hit}')
        accuracy = (pre_hit + post_hit) / (2*len(df))
        print(f'Accuracy: {accuracy}')
        accuracies.append({'model': model, 'condition': condition, 'accuracy': accuracy, 'pre_hit': pre_hit/100, 'post_hit': post_hit/100})

df_accuracies = pd.DataFrame(accuracies)
df_accuracies.to_csv(f"experiments/{scenario}_accuracies.csv", index=False, header=True)

