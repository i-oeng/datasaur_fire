# Intelligent CRM Routing
**Built for the Datasaur Hackathon**


## How to Run Locally

**1. Clone the repository**
```bash
git clone [https://github.com/YourUsername/freedom-routing-engine.git](https://github.com/YourUsername/freedom-routing-engine.git)
cd freedom-routing-engine
```
**2. Set up the virtual environment & install dependencies**

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

**3. Add your environment variables** 
Create a .env.local file in root directory and add your API keys

```bash
OPENAI_API_KEY=your_api_key
```

**4. Run**
```bash
streamlit run app.py
```


## Usage Guide 
1. Upload Data
2. Review raw data
3. Launch AI
4. Export results 
