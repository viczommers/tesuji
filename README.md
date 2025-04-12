# tesuji

### Backend 

```sh
    cd ./backend/ 
    python -m venv venv
    source venv/bin/activate  # On Windows use `.\venv\Scripts\Activate`
    pip install -r requirements.txt
    uvicorn main:app --port 8000 --reload
```

### Frontend

```sh
    cd ./frontend/ 
    npm install # Make sure you have npm installed
    npm run dev
```