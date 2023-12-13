Autores:
- Iago Manoel Brito de Sá Vaz da Silva - 202010135
- Vinicius Caputo de Castro - 202011042

Conteúdos:
- [Criação da aplicação](#criação-da-aplicação)
- [Criação da imagem Docker](#criação-da-imagem-docker)
- [Publicação da imagem](#publicação-da-imagem)
- [Criação dos artefatos no Kubernetes](#criação-dos-artefatos-no-kubernetes)
  - [Dificuldades encontradas](#dificuldades-encontradas)
    - [Como configurar o Chart de dependência](#como-configurar-o-chart-de-dependência)
    - [Credenciais não funcionavam](#credenciais-não-funcionavam)
- [Utilizando a aplicação](#utilizando-a-aplicação)

## Criação da aplicação

Criamos uma aplicação To-Do simples utilizando a linguagem Python e as bibliotecas FastAPI e SQLModel.
O processo foi simples, mesmo que nunca tenhamos utilizado essas bibliotecas,
sendo necessário apenas seguir [o tutorial disponível no site do SQLModel](https://sqlmodel.tiangolo.com/tutorial/fastapi/simple-hero-api/).

A aplicação conta com simples operações CRUD para adicionar, remover, atualizar e listar itens em uma lista de afazeres.

## Criação da imagem Docker

Seguindo para o criação da imagem, criamos um Dockerfile.
Na imagem, é utilizada uma imagem recente do Python como base, são instaladas as dependências, é copiado o código, e é definido o comando para inicializar o contêiner.

Para criar a imagem, o seguinte comando é executado:
```sh
docker build . -t ojogoperdi/devops-app-todo:0.3
```

## Publicação da imagem

Para publicar a imagem:
```sh
docker push ojogoperdi/devops-app-todo:0.3
```

## Criação dos artefatos no Kubernetes

De longe, o passo que mais deu trabalho.

Primeiro, foi necessário criar o Helm Chart.
```sh
helm create todo
```

Para que um banco de dados suba junto a este Chart, foi adicionada uma dependência no `Chart.yaml`:
```yaml
dependencies:
  - name: postgresql
    version: 13.2.24
    repository: https://charts.bitnami.com/bitnami
```

Fizemos a configuração do Chart postgresql pelo `values.yaml`.
```yaml
postgresql:
  auth:
    username: todo
    password: senhasecreta
    database: todo
    enablePostgresUser: false
```

O arquivo `templates/configmap.yaml` foi criado para guardar configurações que serão acessíveis por variáveis de ambiente.
```yaml
kind: ConfigMap
apiVersion: v1
metadata:
  name: {{ include "todo.fullname" . }}-config
  labels:
    {{- include "todo.labels" . | nindent 4 }}
data:
  DB_DIALECT: postgresql
  DB_HOST: {{ .Release.Name }}-postgresql
  DB_NAME: {{ .Values.postgresql.auth.database }}
```

O arquivo `templates/secrets.yaml` foi criado para guardar configurações "secretas" para a aplicação. Aqui, eles são facilmente acessíveis e podem ser trivialmente recuperados ao observar a origem dos valores (`Values.yaml`).
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "todo.fullname" . }}-secret
  labels:
    {{- include "todo.labels" . | nindent 4 }}
type: Opaque
data:
  DB_USER: {{ .Values.postgresql.auth.username | b64enc }}
  DB_PASSWORD: {{ .Values.postgresql.auth.password | b64enc }}
```

Para executar a aplicação, executamos:
```sh
helm install my-todo ./todo
KUBE_POD=$(kubectl get pods --namespace default -l "app.kubernetes.io/name=todo,app.kubernetes.io/instance=my-todo" -o jsonpath="{.items[0].metadata.name}")
kubectl --namespace default port-forward "$KUBE_POD" 8000:8000 --address 0.0.0.0
```

### Dificuldades encontradas

#### Como configurar o Chart de dependência

Alguns tutoriais estavam desatualizados e não utilizavam as chaves yaml corretas para configurar o Chart do postgres.

Na [página do Chart no ArtifactHUB](https://artifacthub.io/packages/helm/bitnami/postgresql), descobrimos que no botão "Values Schema" estão lá descritas as chaves configuráveis.

Também descobrimos que no botão "Install" fica descrito o endereço do repositório e o nome do 
Chart. Os tutoriais não deixaram óbvio como obter essas informações por nós mesmos.

#### Credenciais não funcionavam

Quando a dependência do PostgreSQL foi adicionada, não tínhamos configurado as credenciais iniciais e instalamos o Chart.
Antes de testar a aplicação, adicionamos as credenciais e refizemos a instalação.
A aplicação não conseguiu utilizar as crendiciais fornecidas para se autenticar com o banco de dados.

Depois de muito tempo tentando entender o porquê, descobrimos que o pod do Postgres estava utilizando um volume persistente, onde o banco de dados já foi marcado como inicializado, então as novas credenciais não estavam sendo aplicadas.

Para solucionar esse problema, apagamos o volume, apenas torcendo para que resolvesse o problema.

```sh
kubectl get pvc
# retornou um resultado (data-my-todo-postgresql-0)
kubectl delete pvc data-my-todo-postgresql-0
```

E, com sorte, depois de instalar o Chart, as novas credenciais foram aplicadas.

## Utilizando a aplicação

Em seguida, estão alguns comandos para testá-la e demonstrar suas funcionalidades.
Assumimos que `curl` e `jq` estão instalados.

```sh
APP_URL="http://localhost:8000"

# Função auxiliar para colocar cabeçalho comum em chamadas do curl e formatar sua saída
function curl_json() {
  curl -s -H 'Content-Type: application/json' "$@" | jq .
}

#### Criando itens na lista de To-Do ####

curl_json -X POST -d '{"content": "item um da lista"}' $APP_URL/todo
# {
#  "content": "item um da lista",
#  "done": false,
#  "id": 1,
#  "date": "2023-12-13"
# }

curl_json -X POST -d '{"content": "item dois da lista"}' $APP_URL/todo
# {
#   "content": "item dois da lista",
#   "done": false,
#   "id": 2,
#   "date": "2023-12-13"
# }

#### Listando todos os itens ####

curl_json $APP_URL/todo
# [
#   {
#     "content": "item um da lista",
#     "done": false,
#     "id": 1,
#     "date": "2023-12-13"
#   },
#   {
#     "content": "item dois da lista",
#     "done": false,
#     "id": 2,
#     "date": "2023-12-13"
#   }
# ]

#### Editando os itens ####

curl_json -X PUT -d '{"done": true}' $APP_URL/todo/1
# {
#   "content": "item um da lista",
#   "done": true,
#   "id": 1,
#   "date": "2023-12-13"
# }

curl_json -X PUT -d '{"content": "segundo item da lista"}' $APP_URL/todo/2
# {
#   "content": "segundo item da lista",
#   "done": false,
#   "id": 2,
#   "date": "2023-12-13"
# }

#### Apagando um item ####

curl_json -X DELETE $APP_URL/todo/1
# null

curl_json $APP_URL/todo
# [
#   {
#     "content": "segundo item da lista",
#     "done": false,
#     "id": 2,
#     "date": "2023-12-13"
#   }
# ]
```
