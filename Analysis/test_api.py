import os
import sys
import google.generativeai as genai

def run_hello_gemini():
    """
    A simple script to test the Gemini API with an environment variable.
    """
    print("--- Starting Gemini Hello World Test ---")

    # 1. Load the API key from an environment variable
    # os.getenv() is the perfect tool for this. It returns None if the
    # variable is not found, so we can check for it.
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key is None:
        print("\nERROR: The GEMINI_API_KEY environment variable is not set.")
        print("Please set the variable following the instructions for your OS.")
        # sys.exit() stops the script gracefully.
        sys.exit(1)

    print("Successfully loaded API key from environment.")

    try:
        # 2. Configure the Gemini API with the key
        genai.configure(api_key=api_key)

        # 3. Create a model instance
        # 'gemini-2.0-flash' is a fast and capable model suitable for this test.
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')

        # 4. Define a simple prompt
        prompt = "Hello, world! In one short sentence, what is the key to happiness?"

        print(f"\nSending prompt: '{prompt}'")

        # 5. Send the prompt to the model and get the response
        response = model.generate_content(prompt)

        # 6. Print the response text
        print("\n--- Gemini's Response ---")
        # The response text is accessed via response.text
        print(response.text)
        print("-------------------------\n")
        print("Test completed successfully!")

    except Exception as e:
        # Catch any other exceptions during the API call
        print(f"\nAn error occurred during the API call: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Before running, make sure you have the library installed:
    # pip install google-generativeai
    run_hello_gemini()
