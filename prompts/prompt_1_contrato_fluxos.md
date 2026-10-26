# Prompt Tipo 1: Baseado em Especificação de Contrato e Fluxo de Estado (Specification & Contract-Driven Prompt)

## 1. Classificação e Conceito
- **Tipo de Prompt:** *Specification & Contract-Driven (Baseado em Contrato de API e Especificação OpenAPI)*.
- **Objetivo:** Garantir a conformidade estrutural da API, formatos de requisição e resposta (schemas Pydantic/OpenAPI), códigos de status HTTP apropriados e o ciclo de vida padrão (happy path e unhappy path canônico) da autenticação.

---

## 2. Prompt Enviado à LLM (Template Utilizado)

```text
Atue como um Engenheiro Sênior de QA especializado em testes de integração de APIs REST em Python.

Cenário de Integração:
Estamos integrando o módulo de Autenticação JWT e o módulo de Recursos Protegidos em uma API FastAPI.

Especificação Técnica:
1. POST /api/v1/auth/login
   - Body: {"username": str (min 3), "password": str (min 6)}
   - Sucesso (200): {"access_token": str, "refresh_token": str, "token_type": "Bearer", "expires_in": int}
   - Erro (401): Credenciais inválidas
   - Erro (422): Schema de validação Pydantic violado
2. POST /api/v1/auth/refresh
   - Body: {"refresh_token": str}
   - Sucesso (200): Novo par de tokens
   - Erro (400/401): Token inválido ou expirado
3. POST /api/v1/auth/logout
   - Header: Authorization: Bearer <token>
   - Sucesso (200): Mensagem de encerramento de sessão e revogação do token
4. GET /api/v1/auth/me
   - Header: Authorization: Bearer <token>
   - Sucesso (200): {"id": int, "username": str, "email": str, "role": str, "is_active": bool}
   - Erro (401): Sem token ou token inválido

Gere uma suíte de testes de integração em pytest utilizando TestClient do FastAPI cobrindo:
a) Validação dos contratos de payload e status codes.
b) O fluxo ponta a ponta do ciclo de vida: Login -> Acesso com Bearer -> Refresh do Token -> Acesso com novo token -> Logout -> Tentativa de acesso com token revogado.
Inclua asserções precisas sobre as propriedades retornadas em JSON.
```

---

## 3. Resumo dos Casos de Teste Gerados

1. `test_health_check_contract`: Valida o contrato mínimo de status de saúde da API.
2. `test_login_flow_positive`: Login com credenciais válidas e validação estrutural do retorno JSON (chaves `access_token`, `refresh_token`, tipos e tempo de expiração).
3. `test_login_invalid_credentials`: Submissão de senha incorreta validando status `401 Unauthorized`.
4. `test_login_schema_validation_error`: Submissão de strings menores que os limites do schema, validando status `422 Unprocessable Entity`.
5. `test_protected_route_without_token`: Acesso à rota `/me` sem header Authorization validando status `401`.
6. `test_full_authentication_lifecycle_flow`: Integração completa sequencial de login, consumo, renovação, logout e bloqueio pós-revogação.

---

## 4. Avaliação de Qualidade e Limitações Observadas

- **Pontos Fortes:**
  - Alta precisão na sintaxe e conformidade estrita com o contrato OpenAPI.
  - Testes limpos, diretos e com excelente cobertura do "caminho feliz" e validação estática de schemas.
- **Limitações:**
  - Baixa diversidade de cenários de borda. Não testou comportamento com concorrência, tokens adulterados criptograficamente, nem variações na hierarquia de privilégios dos papéis (RBAC).
