## Deletar todas filas do rabbitmq

```bash
kubectl exec -it -n steam rabbitmq-0 -- sh -c "rabbitmqctl list_queues | grep -v Listing | awk 'NR>2 {print \$1}' | xargs -I{} rabbitmqctl delete_queue {}"
```

## Iniciar Producer

```bash
make start-producer
```

## Para Producer

```bash
make stop-producer
```

## Logs Producer

```bash
kubectl logs -n steam -l app=producer -f
```

## Iniciar Consumer

```bash
# Iniciar consumer para VPS
make start-consumer environment=vps

# Iniciar consumer para Raspberry Pi
make start-consumer environment=rasp-berry
```

## Para Consumer

```bash
make stop-consumer
```

## Logs Consumer

```bash
kubectl logs -n steam -l app.kubernetes.io/instance=consumer -f
```

## Iniciar Stramlit

```bash
make start-streamlit
```

## Para Streamlit

```bash
make stop-streamlit
```

## Logs Streamlit

```bash
kubectl logs -n steam -l app=streamlit -f
```

# Explicação dos campos da aba Queues do RabbitMQ

Na aba **Queues** do RabbitMQ, são exibidos os detalhes das filas configuradas no servidor. Cada campo fornece informações específicas sobre o estado, configuração e métricas das filas. Vou explicar cada um deles:

---

### **1. Name**
- **Descrição**: Nome da fila, definido durante sua criação (pode ser gerado automaticamente se não for fornecido um nome).
- **Exemplo**: `orders_queue`, `email_processing`.

---

### **2. Virtual Host (VHost)**
- **Descrição**: Indica o *Virtual Host* ao qual a fila pertence. Virtual Hosts são ambientes isolados no RabbitMQ, usados para separar recursos (filas, exchanges, etc.) entre aplicações ou equipes.
- **Exemplo**: `/` (VHost padrão), `/production`, `/test`.

---

### **3. Type**
- **Descrição**: Tipo da fila. Os tipos mais comuns são:
  - **Classic**: Fila tradicional do RabbitMQ (não tolerante a partições de rede).
  - **Quorum**: Fila tolerante a partições, baseada em consenso (Raft), ideal para alta disponibilidade.
  - **Stream**: Fila projetada para fluxo contínuo de mensagens, com retenção persistente e consumo sequencial.
- **Exemplo**: `classic`, `quorum`, `stream`.

---

### **4. Features**
- **Descrição**: Características especiais da fila:
  - **D** (Durable): A fila persiste após reinicializações do servidor (se marcada).
  - **E** (Exclusive): Fila exclusiva para uma conexão (é deletada quando a conexão é fechada).
  - **AD** (Auto-Delete): A fila é automaticamente deletada quando o último consumidor se desconecta.
  - **TTL**: Tempo de vida configurado para mensagens ou para a própria fila.
- **Exemplo**: `D` (Duraável), `D, TTL`.

---

### **5. State**
- **Descrição**: Estado atual da fila:
  - **Running**: Funcionando normalmente.
  - **Idle**: Sem atividade (nenhuma mensagem ou consumidor).
  - **Flow**: Pausada devido a controle de fluxo (backpressure).
  - **Down** (em clusters): Replica não disponível.
- **Exemplo**: `running`, `idle`.

---

### **6. Ready / Unacked / Total**
- **Ready**: Número de mensagens prontas para entrega (ainda não consumidas).
- **Unacked**: Mensagens entregues a consumidores, mas ainda não confirmadas (*acknowledged*).
- **Total**: Soma de `Ready` + `Unacked`.
- **Exemplo**: `1000 (Ready) / 50 (Unacked) / 1050 (Total)`.

---

### **7. Message Rates**
- **Incoming**: Taxa de mensagens recebidas (publicadas na fila).
- **Deliver/Get**: Taxa de mensagens entregues a consumidores ou recuperadas via `GET`.
- **Ack**: Taxa de confirmações (*acknowledgments*) recebidas.
- **Exemplo**: `1,000 msg/s (In)`, `500 msg/s (Deliver)`.

---

### **8. Consumers**
- **Descrição**: Número de consumidores ativos inscritos na fila.
- **Relevância**: Se for `0`, as mensagens ficarão acumuladas até que um consumidor se conecte.
- **Exemplo**: `5 consumers`.

---

### **9. Memory**
- **Descrição**: Memória RAM utilizada pela fila (em MB ou KB).
- **Importante**: Filas do tipo *Stream* ou *Lazy* usam menos memória, pois armazenam mensagens em disco.
- **Exemplo**: `45 MB`.

---

### **10. Node**
- **Descrição**: Nó do cluster onde a fila está localizada (em filas clássicas, é o nó mestre).
- **Exemplo**: `rabbit@node1`, `rabbit@node2`.

---

### **11. Policy**
- **Descrição**: Política aplicada à fila (configurações dinâmicas como HA, TTL, limite de tamanho, etc.).
- **Exemplo**: `ha-all` (alta disponibilidade), `max-length-1000` (limite de 1000 mensagens).

---

### **12. Operations**
- **Ações disponíveis**:
  - **Purge**: Remove todas as mensagens prontas (Ready) da fila.
  - **Delete**: Exclui a fila (somente se não houver consumidores).
  - **Export/Import**: Backup/restauração de mensagens (para filas clássicas).
- **Exemplo**: Botões `Purge`, `Delete`.

---

### **Observações Importantes**:
- **Filas Quorum/Stream**: Alguns campos (como `Memory` ou `Node`) podem se comportar diferentemente devido à natureza distribuída desses tipos.
- **Filas Lazy**: Mensagens são armazenadas prioritariamente em disco (útil para filas muito grandes).


estou trabalhando com k3s e helm para fazer o autoscale automatico do script abaixo, que está funcionando perfeitamente para aumentar a quantidade de replicas, porém quando não existe mais itens na fila eles não descem

