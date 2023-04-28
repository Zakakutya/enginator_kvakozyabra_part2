import sys
from flask import Flask, request, render_template, jsonify
import requests
import openai

app = Flask(__name__)
# API key for OpenAI
apikey = "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"
openai.api_key = "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"
#API endpoint for text completion
api_endpoint = "https://api.openai.com/v1/completions"
# Header for the API request
headers = {
    "Accept": "text/event-stream",
    "Authorization": 'Bearer ' + apikey
}
# Data for the API request
data = {
    "model": "text-davinci-003",
    "prompt": "Hello, I'm ChatGPT.",
    "max_tokens": 50,
    "n": 1,
    "temperature": 0.5
}
# Send the request to the API endpoint
response = requests.post(api_endpoint, headers=headers, json=data)
if response.status_code == 200:
    # successful connection
    print("Text API communication established")
    
else:
    # exiting if the connection is not established
    print("Text API communication failed")
    sys.exit()

#Validating the connection to the image API
api_endpoint = "https://api.openai.com/v1/images/generations"
headers = {
    "Authorization": 'Bearer ' + apikey,
    "Content-Type": "application/json"
}
data = {
    "model": "image-alpha-001",
    "prompt": "Hello, I'm ChatGPT.",
    "n": 1,
    "size": "256x256",
    "response_format": "url"
}

response = requests.post(api_endpoint, headers=headers, json=data)
if response.status_code == 200:
    print("Image API communication established")
else:
    print("Image API communication failed")
    #app.stop()
# Array with prompts for each page
results_text = []
# Array with images for each page
results_image = []
# Array with conclusions of prompts for each page
storyconclusion = []

# Function to get the conclusion of the prompt for each page that is used to generate an image
def get_conclusions(stroryArr):
    result = []
    for i in range(len(stroryArr)):
        prompt = f"Write a brief but constructive and understandable conclusion for the paragraph below. \n {stroryArr[i]}"
        result.append(getGptResponse(prompt))
    return result

page = 0
# Function to get the response from the openai API
def getGptResponse(full_prompt):
    response = openai.Completion.create(
        # engine of the API
        engine="text-davinci-003",
        # our prompt for the API
        prompt=full_prompt,
        # max tokens to generate
        max_tokens=2000,
        # number of responses to generate
        n=1,
        stop=None,
        # temperature of the response
        temperature=0.5,
    )
    # returning the response from the API
    return response.choices[0].text.strip()

# Function to manage the text generation. It takes the title of the book and the number of pages as parameters and send to the
# API that creates a fairy tale with the given title and number of pages. Then it splits the text into sentences and pairs of sentences
# and stores each page prompt in the array
def manage_text(title, num_pages):
    # prompt for the API
    prompt = f"Write a fairy tale titled '{title}' that is {num_pages * 2} sentences long:"
    story = getGptResponse(prompt)
    # cleaning the data
    sentences = story.replace("\n", ". ").split(". ")

    # Remove any empty sentences
    sentences = [s for s in sentences if s]

    # Create a new list to hold the split sentences
    split_sentences = []

    # Loop over the sentences and append pairs of sentences to the new list
    for i in range(0, len(sentences), 2):
        if i+1 < len(sentences):
            split_sentences.append(sentences[i] + ". " + sentences[i+1] + ".")
        else:
            split_sentences.append(sentences[i])
    #create string from split sentences
    stre = ""
    for i in range(len(split_sentences)):
        stre += split_sentences[i] + "\n" 
    prompt = f"Perefrace {stre} into a {num_pages} amount of pages, amount of pages is {num_pages} but amount of sentences per page is not fixed."
    report = getGptResponse(prompt)
    string = report.replace("\n\n", "\n")

    # split into pages
    pages = []
    page_start = 0
    # loop over the pages and append them to the array
    for i in range(string.count("Page ")):
        page_end = string.find("Page ", page_start + 1)
        if page_end == -1:
            page_end = len(string)
        page_text = string[string.find("\n", page_start) + 1:page_end].strip()
        pages.append(page_text)
        page_start = page_end

    return pages

@app.route("/")
def index():
    return render_template('web.html')

# Function to get the image from the openai API
def getDalleResponse(prompt):
    response = openai.Image.create(
        prompt=prompt,
        model="image-alpha-001",
        size="256x256",
        response_format="url"
    )
    return response["data"][0]["url"]

#function is used to get request from web page
@app.route("/submit", methods=["POST"])
def submit():
    title = request.json["title"]
    length_value = request.json["length"]
    global results_text
    global results_image
    global storyconclusion
    global page
    results_text = manage_text(title, length_value)
    storyconclusion = get_conclusions(results_text)
    results_text.insert(0, title)
    storyconclusion.insert(0, f"generate a beautiful book cover page for {title} in Fairy Tale style")
    
    results_image.append(getDalleResponse(storyconclusion[0]))
    results_image.append(getDalleResponse(f"generate a beautiful image {storyconclusion[1]} in Fairy Tale style"))
    
    return jsonify({'result':f"Our magic system created a Fairy Tale \n about {title}", 'length': length_value, 'page': f"Page number is {page}", 'image': results_image[0]})

# defines a route for the "/Next" URL path, which accepts HTTP POST requests
# used if the user wants to see the next page of the book
@app.route("/Next", methods=["POST"])
def Next():
    global results_text
    global results_image
    global storyconclusion
    global page
    
    if page >= len(results_text):
        page = len(results_text) - 1
        return jsonify({'result': results_text[page], 'page': f"Page number is {page}", 'image': results_image[page], 'active': False})
        
    if page < len(results_text) - 1:
        page += 1
    
    if page < len(results_text) - 1:
        if len(results_image) < page + 2 or len(results_image[page + 1]) <= 1:
            results_image.append(getDalleResponse(f"generate a beautiful image {storyconclusion[page+1]} in Fairy Tale style"))
            
    return jsonify({'result': results_text[page], 'page': f"Page number is {page}", 'image': results_image[page], 'active': True})


#defines a route for the "/Back" URL path, which accepts HTTP POST requests
# used if the user wants to see the previous page of the book
@app.route("/Back", methods=["POST"])
def Back():
    global results_text
    global results_image
    global page
    if page > 0:
        page = page - 1
    return jsonify({'result': results_text[page], 'page': f"Page number is {page}", 'image': results_image[page]})


if __name__ == "__main__":
    app.run(debug=True)
