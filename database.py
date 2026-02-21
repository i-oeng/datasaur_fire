from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os
load_dotenv(".env.local")
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

if not DATABASE_URL:
    st.error("DATABASE_URL не найден в .env.local.")
    st.stop()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class BusinessUnit(Base):
    __tablename__ = "business_units"
    id = Column(Integer, primary_key=True, index=True)
    office_name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=True) 
    longitude = Column(Float, nullable=True)

class Manager(Base):
    __tablename__ = "managers"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False) # Спец, Ведущий спец, Глав спец
    skills = Column(String, nullable=False) 
    unit_name = Column(String, nullable=False) 
    current_load = Column(Integer, default=0)

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    client_guid = Column(String, nullable=False)
    gender = Column(String)
    birth_date = Column(String)
    segment = Column(String) 
    description = Column(Text)
    attachment = Column(String)
    country = Column(String)
    region = Column(String)
    city = Column(String)
    street = Column(String)
    building = Column(String)
    
class RoutingResult(Base):
    __tablename__ = "routing_results"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    assigned_manager_id = Column(Integer, ForeignKey("managers.id"))

    ai_type = Column(String)
    ai_sentiment = Column(String)
    ai_priority = Column(Integer)
    ai_language = Column(String)
    ai_summary = Column(Text)



def init_db():
    print("Dropping old tables...")
    Base.metadata.drop_all(bind=engine) 
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    init_db()

