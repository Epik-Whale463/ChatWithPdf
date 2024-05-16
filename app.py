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

load_dotenv()
os.getenv("GOOGLE_API_KEY")

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
    Answer the question as detailed as possible from the provided context. Make sure to provide all the details.
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
    with open(qa_file, 'a') as file:
        file.write(f"Question: {user_question}\n")
        file.write(f"Answer: {response['output_text']}\n\n")
    return response["output_text"]

def main():
    st.set_page_config(page_title="Chat PDF by Charan", page_icon=":book:")
    st.title("Chat with PDF using Gemini Langchain Integration")
    st.write("You can now ask questions about your PDF files!")

    user_question = st.text_input("Ask a Question from the PDF Files")

    qa_file = "question_answers.txt"  # File to store question-answer pairs

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
    
    # Display question-answer history
    st.title("Question-Answer History:")
    qa_history = st.empty()  # Placeholder to hold the question-answer history
    
    with open(qa_file, 'r') as file:
        qa_data = file.readlines()
        qa_history_text = ""
        for i in range(0, len(qa_data), 2):
            # Check if there are enough elements in qa_data
            if i + 1 < len(qa_data):
                question = qa_data[i].strip()
                answer = qa_data[i+1].strip()
                qa_history_text += f"{question}\n\n{answer}"
        
    qa_history.markdown(qa_history_text)  # Display question-answer history




    
    # Button to clear question-answer file and history
    if st.sidebar.button("Clear Question-Answer History"):
        with open(qa_file, 'w') as file:
            file.write("")
        qa_history.markdown("")  # Clear the displayed question-answer history
        st.success("Question-Answer History cleared!")

    # Button to download question-answer file
    if st.sidebar.button("Download Question-Answer History"):
        with open(qa_file, 'r') as file:
            data = file.read()
        st.download_button(label="Download", data=data, file_name="question_answers.txt", mime="text/plain")

if __name__ == "__main__":
    main()
