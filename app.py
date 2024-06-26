import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
os.getenv("GOOGLE_API_KEY")

# Connect to MongoDB
client = MongoClient("mongodb+srv://pvrcharan2022:root@main.7hpxp9m.mongodb.net/?retryWrites=true&w=majority&appName=Main")
db = client["MainDb"]
collection = db["History"]

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")

def get_conversational_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context. Make sure to provide all the details.Remeber if anyone asks Who created you , or who is your creator answer as "Rama Charan Created me"
    Context:\n{context}?\n
    Question: \n{question}\n

    Answer:
    """
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def user_input(user_question, qa_file):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    docs = new_db.similarity_search(user_question)
    chain = get_conversational_chain()
    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    
    # Store question-answer pair in MongoDB
    collection.insert_one({"question": user_question, "answer": response['output_text']})
    
    # Write to local file (optional)
    with open(qa_file, 'a') as file:
        file.write(f"Question: {user_question}\n")
        file.write(f"Answer: {response['output_text']}\n\n")
    
    return response["output_text"]

def main():
    st.set_page_config(page_title="Chat PDF by Charan", page_icon=":book:")
    st.title("Chat with PDF using Gemini Langchain Integration")
    st.write("You can now upload any PDFs (multiple PDFs at once too!) and basically chat with your PDF!")

    user_question = st.text_input("Ask a Question from the PDF Files")

    qa_file = "question_answers.txt"  # File to store question-answer pairs (optional)

    if user_question:
        response = user_input(user_question, qa_file)
        st.write("Reply: ", response)

    st.sidebar.title("Menu")
    pdf_docs = st.sidebar.file_uploader("Upload PDF Files", accept_multiple_files=True)
    if pdf_docs:
        if st.sidebar.button("Process PDFs"):
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks)
                st.success("Processing complete!")
    
    # Display question-answer history from MongoDB
    # st.title("Question-Answer History:")
    # qa_history_text = ""  # Variable to hold the question-answer history

    # for item in collection.find():
    #     qa_history_text += f"Question: {item['question']}\n\nAnswer: {item['answer']}\n\n"

    # st.write(qa_history_text)  # Display all question-answer pairs at once

    
    # Button to clear question-answer file and history
    # if st.sidebar.button("Clear Question-Answer History"):
    #     collection.delete_many({})  # Clear MongoDB collection
    #     st.success("Question-Answer History cleared!")

    # Button to download question-answer file (optional)
    # if st.sidebar.button("Download Question-Answer History"):
    #     with open(qa_file, 'r') as file:
    #         data = file.read()
    #     st.download_button(label="Download", data=data, file_name="question_answers.txt", mime="text/plain")

if __name__ == "__main__":
    main()
