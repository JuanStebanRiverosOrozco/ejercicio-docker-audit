from app import app


def test_health_ok():
    cliente = app.test_client()
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"status": "ok"}


def test_home_sin_base_de_datos():
    cliente = app.test_client()
    respuesta = cliente.get("/")
    assert respuesta.status_code == 503


def test_buscar_sin_base_de_datos():
    cliente = app.test_client()
    respuesta = cliente.get("/buscar?id=1")
    assert respuesta.status_code == 500
    assert respuesta.get_json()["error"]


def test_buscar_no_expone_query_inyectada():
    cliente = app.test_client()
    respuesta = cliente.get("/buscar?id=1;DROP TABLE usuarios")
    assert respuesta.status_code == 500
    assert "DROP TABLE" not in respuesta.get_data(as_text=True)