import anthropic
import json

client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="your_api_key"
)

#models = ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]

model_alias = {"claude-3-haiku-20240307" : "haiku",
               "claude-3-sonnet-20240229" : "sonnet",
                "claude-3-opus-20240229" : "opus"
                }

def replace_with_misspelled(sample_text: str, word: str, replacement: str) -> str:
    return sample_text.replace(word, replacement)

def generate_sample_text(model: str, word: str) -> str:
    message = client.messages.create(
        model=model,
        max_tokens=1000,
        temperature=0.0,
        system="Please make sure to use the maximum number of tokens available to sample. Do not repeat the user request in your response.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please write a short story about San Francisco. This short story must contain the word \"" + word + "\" exactly once."
                    }
                ]
            }
        ]
    )
    
    sample_text = message.content[0].text.replace('\n\n', '\n').replace('\n', ' ')
    num_occurrences = sample_text.count(word)
    if num_occurrences > 1:
        print(f"Warning: The word \"{word}\" appears more than once in the generated text. Please ensure that the word is used exactly once.")
    
    return sample_text, num_occurrences

scenario = "scenario_1"
model = "claude-3-haiku-20240307" # test haiku

correct_to_misspelled = {"beautiful" : "beatiful"
                        "Caribbean" : "Carribean",
                        "cemetery" : "cemetary",
                        "occurrence" : "occurrance",
                        "publicly" : "publically"
                         }

num_samples_per_word = 20
results = []

for word, replacement in correct_to_misspelled.items():
    for i in range(1, num_samples_per_word + 1):
        # discard samples that contain the word more than once
        while True:
            correct_sample, num_occurrences = generate_sample_text(model, word)
            if num_occurrences == 1:
                break
        misspelled_sample = replace_with_misspelled(correct_sample, word, replacement)
        results.append({"model": model,
                         "correct_word": word,
                         "misspelled_word": replacement,
                         "correct_sample_text": correct_sample,
                         "misspelled_sample_text": misspelled_sample,
                         "sample_number": i})

with open(f"experiments/{scenario}.json", "w") as f:
    json.dump(results, f, indent=4)
