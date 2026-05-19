from app.clients.models.client_record import ClientRecord


def scope_to_active_clients_stmt(stmt, owner_model):
    return stmt.join(ClientRecord, ClientRecord.id == owner_model.client_record_id).where(
        ClientRecord.deleted_at.is_(None)
    )
