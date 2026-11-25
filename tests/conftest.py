import pytest

from paineis.comum import dados


def pytest_configure(config):
    config.addinivalue_line("markers", "lento: roda o ELT completo (cerca de 1 a 2 minutos)")


@pytest.fixture(scope="session")
def publicado():
    """Os testes dos painéis leem o que o último `python -m elt` publicou."""
    if not (dados.PASTA_PUBLICADO / "_manifesto.json").exists():
        pytest.skip("Rode `python -m elt` antes dos testes dos painéis.")


@pytest.fixture(scope="session")
def servidor(publicado):
    """(cliente HTTP de teste, {nome: app Dash}) com os três painéis no mesmo servidor."""
    from paineis.servidor import criar_servidor

    srv = criar_servidor()
    return srv.test_client(), srv.paineis
