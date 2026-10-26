# Prompt Tipo 2: Baseado em Matriz RBAC, Casos Limite e Abordagem Adversarial (Adversarial & RBAC Security Prompt)

## 1. Classificação e Conceito
- **Tipo de Prompt:** *Adversarial, Boundary & Security-Driven Prompt (Matriz de Acesso e Cenários de Quebra)*.
- **Objetivo:** Forçar a LLM a pensar como um *Security QA / Pentester*, focando nas falhas de comunicação, quebra de autorização (RBAC), escalonamento de privilégios (Privilege Escalation), ataques de repetição (Replay Attacks) e integridade criptográfica de tokens entre os módulos de Autenticação, Recursos e Auditoria.

---

## 2. Prompt Enviado à LLM (Template Utilizado)

```text
Atue como um Engenheiro Especialista em Testes de Segurança de Software (AppSec / QA Automation).

Cenário de Integração:
Sistema de gestão de documentos com controle de acesso baseado em papéis (RBAC):
- Papéis: Admin (total), Editor (cria/edita), Viewer (apenas leitura de não confidenciais).
- Controles: JWT (access + refresh com rotação), flag de usuário inativo, middleware de auditoria.

Matriz de Acesso:
- GET /api/v1/documents: Admin e Editor vêem tudo; Viewer vê apenas is_confidential=False.
- POST /api/v1/documents: Admin e Editor permitidos; Viewer recebe 403 Forbidden.
- DELETE /api/v1/documents/{id}: Apenas Admin permitido; Editor e Viewer recebem 403 Forbidden.
- POST /api/v1/auth/refresh: Realiza rotação; reuso do token antigo deve ser bloqueado com 401.
- Contas com is_active=False: Bloqueadas tanto no login (403) quanto no consumo de APIs com token antigo (403).
- Logs de Auditoria: Qualquer tentativa proibida ou permitida em rotas /api/v1 deve persistir registro no módulo de auditoria.

Gere uma suíte de testes de integração com pytest e FastAPI TestClient com foco ADVERSARIAL e CASOS LIMITE:
1. Teste de tentativa de escalonamento vertical (Viewer criando doc; Editor deletando doc).
2. Teste de vazamento de dados (Garantir que doc confidencial nunca apareça na resposta do Viewer).
3. Teste de token adulterado (assinatura com chave secreta forjada de atacante).
4. Teste de token expirado artificialmente.
5. Teste de confusão de token (passar refresh_token no header Bearer de rota protegida).
6. Teste de Replay Attack em rotação de refresh token.
7. Teste de bloqueio de usuário inativo com token válido pré-existente.
8. Teste de auditoria transversal: verificar se a tentativa de violação (403) foi devidamente registrada nos logs de auditoria.
```

---

## 3. Resumo dos Casos de Teste Gerados

1. `test_rbac_privilege_escalation_viewer_cannot_create_document`: Tentativa do Viewer criar documento barrada com HTTP 403.
2. `test_rbac_privilege_escalation_editor_cannot_delete_document`: Tentativa do Editor deletar documento barrada com HTTP 403.
3. `test_rbac_data_segregation_confidential_documents_filtered_for_viewer`: Garante que documentos confidenciais são filtrados para Viewer, mas exibidos para Admin.
4. `test_forged_signature_token_rejected`: Token assinado com chave arbitrária de terceiro é rejeitado com HTTP 401.
5. `test_expired_token_rejected`: Token expirado não é aceito pelas rotas protegidas (HTTP 401).
6. `test_refresh_token_used_as_access_token_rejected`: Envio de refresh token no header de autorização é barrado por validação de claim `type`.
7. `test_token_rotation_prevents_replay_attack`: Refresh token rotacionado é adicionado à lista de revogação; segunda chamada é rejeitada.
8. `test_inactive_user_cannot_login_and_cannot_access_routes`: Contas inativas são impedidas no login e no consumo de endpoints.
9. `test_audit_logs_record_forbidden_and_authorized_actions`: Validação cruzada com o módulo de auditoria, verificando se a violação gerou registro rastreável.

---

## 4. Avaliação de Qualidade e Ajustes Necessários

- **Pontos Fortes:**
  - Elevada profundidade e diversidade de cenários de falha.
  - Testou interações reais entre diferentes microsserviços/módulos lógicos (Auth <-> Banco <-> Auditoria <-> Autorização).
- **Ajustes e Refinamentos Aplicados:**
  - **Identificador Único (`jti`):** Tokens gerados na mesma fração de segundo para rotação tinham hash idêntico em testes rápidos; foi necessário instruir a LLM / código a incluir `jti` (UUID) nos tokens.
  - **Tamanho da Chave HMAC:** Ajustou-se o segredo de teste para > 32 bytes (256 bits) conforme RFC 7518 para conformidade criptográfica estrita.
  - **Mocks Compartilhados:** Uso de fixtures pytest (`conftest.py`) para evitar duplicação do setup de usuários e cabeçalhos em cada teste.
