from sqlmodel import Field, SQLModel, Session, create_engine, select, delete


# Data Models
class ExtraRequest(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    request: str


class Database:
    def __init__(self):
        # Setup the database
        self.engine = create_engine("sqlite:///database.db")
        SQLModel.metadata.create_all(self.engine)

    def select_all_extra_requests(self):
        with Session(self.engine) as session:
            return session.exec(select(ExtraRequest)).all()
    
    def select_extra_req_by_id(self, id: int | str):
        if type(id) is str:
            try:
                id = int(id) # Best effort to convert to int
            except:
                pass
        with Session(self.engine) as session:
            return session.exec(select(ExtraRequest).where(id=id)).first()
    
    def add_extra_request(self, request: int):
        extra_request = ExtraRequest(request=request)
        with Session(self.engine) as session:
            session.add(extra_request)
            session.commit()
    
    def remove_extra_request_by_id(self, id):
        if type(id) is str:
            try:
                id = int(id) # Best effort to convert to int
            except:
                pass
        with Session(self.engine) as session:
            session.exec(delete(ExtraRequest).where(id=id))
    

        