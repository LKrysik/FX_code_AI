import psycopg2
import json

conn = psycopg2.connect(host='127.0.0.1', port=8812, user='admin', password='quest', database='qdb')
cur = conn.cursor()
cur.execute("SELECT id, strategy_name, strategy_json FROM strategies WHERE strategy_name = 'E2E Pump Test' ORDER BY created_at DESC LIMIT 1")
row = cur.fetchone()
if row:
    print(f'ID: {row[0]}')
    print(f'Name: {row[1]}')
    strategy_json = json.loads(row[2])
    print(f'S1 conditions:')
    for cond in strategy_json.get('s1_signal', {}).get('conditions', []):
        print(f'  - {cond}')
conn.close()
