from app.services.vidal_service import VidalService


def test_parse_vidal_search_result_metadata() -> None:
    source = '''
    <table><tr>
      <td class="products-table-loz"><img alt="Без рецепта"></td>
      <td class="products-table-name">
        <a class="no-underline" href="/drugs/paracetamol__18544">Парацетамол</a>
      </td>
      <td class="products-table-zip">
        <div class="hyphenate">Суппозитории ректальные 50 мг: 10 шт.</div>
        <span>РУ: ЛП-№(009887)-(РГ-RU) от 22.04.25</span>
      </td>
      <td class="products-table-company">
        <a href="/drugs/firm/6581">ПРОМОМЕД РУС</a><span>(Россия)</span>
      </td>
    </tr></table>
    '''

    results = VidalService.parse_search_results(source)

    assert len(results) == 1
    result = results[0]
    assert result.name == "Парацетамол"
    assert result.url == "https://www.vidal.ru/drugs/paracetamol__18544"
    assert result.release_form == "Суппозитории ректальные 50 мг: 10 шт."
    assert result.registration == "РУ: ЛП-№(009887)-(РГ-RU) от 22.04.25"
    assert result.company == "ПРОМОМЕД РУС (Россия)"
    assert result.availability == "Без рецепта"
