from app.clients.models.client_record import ClientRecord


def scope_to_active_clients(query, owner_model):
    return (
        query.join(ClientRecord, ClientRecord.id == owner_model.client_record_id)
        .filter(ClientRecord.deleted_at.is_(None))
    )
