# Painel de OEE — Produção com Injetoras

Dashboard em Streamlit com os indicadores de produção (disponibilidade, performance,
qualidade, OEE e Pareto de paradas) calculados na fase 2 do projeto.

## Estrutura

```
app.py                 → aplicação Streamlit
requirements.txt       → dependências
data/                  → CSVs limpos (produção, paradas, ordens, produtos)
assets/                → logo Davi Rocha (colorido e branco)
```

## Rodar localmente

```
pip install -r requirements.txt
streamlit run app.py
```

## Deploy no Streamlit Community Cloud

1. Suba esta pasta inteira (com `data/` e `assets/`) para um repositório no GitHub.
2. Em share.streamlit.io, aponte para o repositório e o arquivo `app.py`.
3. O deploy usa o `requirements.txt` automaticamente.

## Sobre os dados

`data/produtos.csv` é o cadastro de produtos **recalibrado** (o tempo de ciclo
padrão original não batia com o throughput real dos dados de produção — foi
ajustado para refletir o que os dados realmente mostram). Se algum dado de
produção ou parada for atualizado no futuro, os KPIs recalculam sozinhos —
todo o cálculo acontece dentro do `app.py`, não em arquivos pré-processados.

Projeto de demonstração — dados simulados, para portfólio.
