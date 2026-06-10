# Da Pra Lavar A Roupa?

Um projeto pessoal desenvolvido para resolver o problema de saber qual é o melhor dia para lavar roupa analisando as condições climáticas.

## Sobre o Projeto

Este é um aplicativo Streamlit que utiliza dados de previsão meteorológica para determinar os melhores dias para realizar a atividade de lavar roupas. A aplicação analisa diversos fatores climáticos como temperatura, umidade, precipitação, velocidade do vento e cobertura de nuvens para fornecer recomendações personalizadas.

## Objetivo

O principal objetivo é solucionar a dúvida recorrente: **"Qual é o melhor dia para lavar a roupa?"**. Através da análise de dados meteorológicos dos próximos 5 dias, o app fornece um ranking dos dias mais adequados para secar roupa ao ar livre, considerando as condições climáticas ideais.

## Funcionalidades

- Busca por localização via CEP (formato: 01310-200 ou 01310200)
- Análise detalhada de condições climáticas para os próximos 5 dias
- Sistema de scoring baseado em múltiplos fatores:
  - Temperatura
  - Umidade relativa do ar
  - Precipitação
  - Velocidade do vento
  - Cobertura de nuvens
- Recomendações personalizadas dos melhores dias para lavar roupa

## Funcionalidades Futuras

- **Notificações por Email**: O projeto terá suporte a envio de notificações por email para alertar o usuário sobre os melhores dias para lavar roupa

## Como Usar

1. Execute a aplicação Streamlit - https://dapralavararoupa.streamlit.app/
2. Digite seu CEP (código postal brasileiro)
3. Clique em "Resumo" para ver a análise dos próximos 5 dias
4. Consulte as recomendações e escolha o melhor dia para lavar suas roupas!

## Estrutura do Projeto

```
Da-Pra-Lavar-A-Roupa/
├── app.py                    # Aplicação principal Streamlit
├── src/
│   ├── data_ingestion.py    # Ingestão de dados meteorológicos
│   ├── send_email.py         # Módulo para envio de emails (futuro)
│   └── utils.py              # Funções utilitárias
├── requirements.txt          # Dependências do projeto
└── README.md                 # Este arquivo
```

## Tecnologias Utilizadas

- **Streamlit**: Framework para criar aplicações web em Python
- **Pandas**: Análise e manipulação de dados
- **OpenWeatherMap API**: Dados de previsão meteorológica
- **Python**: Linguagem de programação principal

## Instalação

```bash
pip install -r requirements.txt
```

## Execução

```bash
streamlit run app.py
```

## Licença

Consulte o arquivo LICENSE para mais informações.
