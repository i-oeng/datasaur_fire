import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
from main import analyze_ticket_text 
from dotenv import load_dotenv
from router import route_ticket
from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
import concurrent.futures


load_dotenv(".env.local")
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

if not DATABASE_URL:
    st.error("DATABASE_URL не найден в .env.local.")
    st.stop()

st.set_page_config(page_title="Freedom Ticket Routing", layout="wide")
st.title("Intelligent CRM Routing")


st.header("Загрузка новых обращений")
uploaded_file = st.file_uploader("", type=["csv"])

if uploaded_file is not None:
    try:
        df_new_tickets = pd.read_csv(uploaded_file)
        df_new_tickets.columns = df_new_tickets.columns.str.strip()
        df_new_tickets = df_new_tickets.rename(columns={
            "GUID клиента": "client_guid", "Пол клиента": "gender",
            "Дата рождения": "birth_date", "Сегмент клиента": "segment",
            "Описание": "description", "Вложения": "attachment",
            "Страна": "country", "Область": "region",
            "Населённый пункт": "city", "Улица": "street", "Дом": "building"
        })
        with st.spinner('Загрузка в базу данных...'):
            df_new_tickets.to_sql("tickets", con=engine, if_exists="append", index=False)
        st.success(f"Успешно загружено {len(df_new_tickets)} новых обращений.")
    except Exception as e:
        st.error(f"Ошибка при загрузке: {e}")

st.divider()


st.header("Текущая база обращений")
try:
    df_db_tickets = pd.read_sql("SELECT * FROM tickets", engine)
    if not df_db_tickets.empty:
        with st.expander("Просмотреть сырые данные"):
            st.dataframe(df_db_tickets, height=200)
            
        col1, col2 = st.columns(2)
        with col1:
            fig_segment = px.pie(df_db_tickets, names='segment', title='Распределение по сегментам', hole=0.4)
            st.plotly_chart(fig_segment, use_container_width=True)
        with col2:
            city_counts = df_db_tickets['city'].value_counts().reset_index()
            city_counts.columns = ['city', 'count']
            fig_city = px.bar(city_counts, x='city', y='count', title='Количество обращений по населённым пунктам/городам')
            st.plotly_chart(fig_city, use_container_width=True)
    else:
        st.info("База данных обращений пуста. Загрузите CSV файл выше.")
except Exception as e:
    st.error(f"Не удалось подключиться к базе данных: {e}")

st.divider()


st.header("Анализ")

try:
    total_tickets = pd.read_sql("SELECT COUNT(*) FROM tickets", engine).iloc[0,0]
    processed_tickets = pd.read_sql("SELECT COUNT(*) FROM routing_results", engine).iloc[0,0]
    pending_tickets = total_tickets - processed_tickets
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Всего обращений", total_tickets)
    col2.metric("Уже обработано", processed_tickets)
    col3.metric("На очереди", pending_tickets)
except Exception as e:
    st.warning("Загрузите данные, чтобы увидеть статистику.")

st.divider()

if pending_tickets > 0:
    num_to_process = st.slider("Сколько новых тикетов обработать за раз?", min_value=1, max_value=20, value=min(5, pending_tickets))

    if st.button("Запустить анализ"):
        
        query_unprocessed = f"""
            SELECT id, description, attachment 
            FROM tickets 
            WHERE id NOT IN (SELECT ticket_id FROM routing_results)
            ORDER BY id DESC 
            LIMIT {num_to_process}
        """
        df_unprocessed = pd.read_sql(query_unprocessed, engine)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text(f"Отправка тикетов...")
        ai_responses = {}
        
        def fetch_ai(row):
            img_path = str(row['attachment']).strip() if pd.notna(row['attachment']) else None
            if img_path and img_path.lower() in ['nan', 'none', '']:
                img_path = None

            return row['id'], analyze_ticket_text(row['description'], image_path=img_path)


        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticket = {executor.submit(fetch_ai, row): row for _, row in df_unprocessed.iterrows()}
            
            completed_ai = 0
            for future in concurrent.futures.as_completed(future_to_ticket):
                ticket_id, ai_data = future.result()
                ai_responses[ticket_id] = ai_data
                completed_ai += 1
                progress_bar.progress(completed_ai / (len(df_unprocessed) * 2)) 

        status_text.text("ИИ завершил работу. Маршрутизация и балансировка нагрузки...")
        results_list = []
        current_step = 0
        
        for index, row in df_unprocessed.iterrows():
            tid = row['id']
            ai_data = ai_responses[tid]
            

            assigned_name, office = route_ticket(tid, engine, ai_data)
            

            insert_query = text("""
                INSERT INTO routing_results (ticket_id, ai_type, ai_sentiment, ai_priority, ai_language, ai_summary, assigned_manager_id)
                VALUES (:tid, :typ, :sen, :pri, :lan, :sum, :mgr)
            """)
            
            manager_id_query = text(f"SELECT id FROM managers WHERE full_name = '{assigned_name}'")
            
            with engine.begin() as conn:
                mgr_id_result = conn.execute(manager_id_query).fetchone()
                mgr_id = mgr_id_result[0] if mgr_id_result else None
                
                conn.execute(insert_query, {
                    "tid": tid, "typ": ai_data['ticket_type'], "sen": ai_data['sentiment'],
                    "pri": ai_data['priority'], "lan": ai_data['language'], "sum": ai_data['summary'],
                    "mgr": mgr_id
                })

            ai_data['ticket_id'] = tid
            ai_data['assigned_manager'] = assigned_name
            ai_data['office'] = office
            results_list.append(ai_data)
            
            current_step += 1

            progress_bar.progress(0.5 + (current_step / (len(df_unprocessed) * 2)))
            
        status_text.success(f"Обработка завершена {len(df_unprocessed)} тикетов.")
        st.subheader("Результаты текущей сессии")
        st.dataframe(pd.DataFrame(results_list))
        
        if st.button("Обновить статистику"):
            st.rerun()
else:
    st.success("Все доступные тикеты успешно распределены")


st.header("Итоговое распределение обращений")
st.write("Связь: Клиент -> Аналитика ИИ -> Назначенный менеджер")

try:

    query_results = """
        SELECT 
            t.id AS "Ticket ID",
            t.segment AS "Сегмент",
            t.description AS "Текст обращения",
            r.ai_type AS "Категория (ИИ)",
            r.ai_priority AS "Приоритет",
            r.ai_language AS "Язык",
            r.ai_summary AS "Summary",
            m.full_name AS "Назначенный Менеджер",
            m.unit_name AS "Офис Менеджера"
        FROM routing_results r
        JOIN tickets t ON r.ticket_id = t.id
        JOIN managers m ON r.assigned_manager_id = m.id
        ORDER BY r.ticket_id DESC
    """
    df_final_results = pd.read_sql(query_results, engine)
    
    if not df_final_results.empty:

        st.dataframe(df_final_results, use_container_width=True, height=400)
        

        csv = df_final_results.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="Скачать результаты (CSV)",
            data=csv,
            file_name='freedom_routing_results.csv',
            mime='text/csv',
        )
    else:
        st.info("Нет обработанных тикетов. Запустите ИИ-анализ в блоке выше.")

except Exception as e:
    st.error(f"Ошибка при загрузке результатов: {e}")


st.divider()
st.header("ИИ-Аналитик")
st.write("Задавайте любые вопросы по распределенным тикетам.")

if 'df_final_results' in locals() and not df_final_results.empty:
    
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0)
    

    agent = create_pandas_dataframe_agent(
        llm, 
        df_final_results, 
        verbose=True, 
        agent_type="openai-tools",
        allow_dangerous_code=True 
    )
    

    user_question = st.text_input("Ваш запрос (например: Выведи топ-3 менеджеров по количеству назначенных тикетов):")
    
    if st.button("Спросить ИИ-Аналитика"):
        if user_question:
            with st.spinner("Анализирую массив данных..."):
                try:

                    response = agent.invoke(user_question)
                    

                    st.success(response["output"])
                    
                except Exception as e:
                    st.error(f"Произошла ошибка при анализе: {e}")
        else:
            st.warning("Пожалуйста, введите вопрос.")
else:
    st.info("Сначала обработайте тикеты, чтобы ассистенту было с чем работать.")