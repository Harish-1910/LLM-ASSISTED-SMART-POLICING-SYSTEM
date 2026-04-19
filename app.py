from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import os
from dotenv import load_dotenv

#  LangChain Imports
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_groq import ChatGroq   

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecret"

#  LangChain LLM (Groq)
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant",
    temperature=0.4
)

#  Prompt Template
prompt_template = PromptTemplate(
    input_variables=["query", "data"],
    template="""
You are an intelligent crime data analyst.

User Query:
{query}

Relevant Crime Dataset Records:
{data}

Instructions:
- Explain what crimes occurred
- Identify trends or patterns
- Mention frequency or severity if visible
- Provide analytical insights in paragraph format
"""
)

#  Chain
chain = LLMChain(llm=llm, prompt=prompt_template)

# In-memory users
users = {}

# Load dataset
CSV_PATH = "crime_data.csv"

if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH)
    df["combined_text"] = df.astype(str).agg(" ".join, axis=1).str.lower()
else:
    df = None


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in users:
            return "User already exists!"

        users[username] = generate_password_hash(password)
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in users and check_password_hash(users[username], password):
            session["user"] = username
            return redirect(url_for("dashboard"))

        return "Invalid credentials!"

    return render_template("login.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    result = None
    query = None

    if request.method == "POST":

        query = request.form.get("query")
        dataset_context = "No relevant dataset records were found."

        # 🔍 Data filtering
        if df is not None and query:
            filtered = df[df["combined_text"].str.contains(query.lower(), na=False)]

            if not filtered.empty:
                dataset_context = filtered.head(15).drop(columns=["combined_text"]).to_string(index=False)

        #  LangChain Call
        response = chain.run({
            "query": query,
            "data": dataset_context
        })

        result = response

    return render_template("page1.html", result=result, query=query)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
