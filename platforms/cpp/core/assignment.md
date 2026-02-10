V následujícím zadání chybí cíl, kterého má řešení dosáhnout, přičemž prozrazuje, jak vypadá jedno správné řešení (neexistujícího) problému:
```
Naprogramujte v jazyce C++ vícevláknovou interaktivní službu, která bude na jednom vlákně čekat na příkazy, vkládat je do fronty a další vlákna budou na pozadí tyto příkazy vykonávat. Počet vláken pro vykonávání omezte na hodnotu v řádu nižších jednotek (cca 2-4). Zadávání příkazů bude probíhat přes příkazovou řádku.

Podporované příkazy:
* Vypnutí - zajistí ukončení hlavní služby poté, co běžící vlákna ukončí svou práci. Zatím nezpracované požadavky ve frontě budou zahozeny.
* Stažení souboru z URL - vloží do fronty URL souboru, který pak nějaké pracovní vlákno bude stahovat.

./webgrab # spustím službu, další příkazy už vstupují na stdin
> download www.neco.cz/soubor
> download www.necojineho.cz/soubor2
> quit

Konkrétní detaily implementace jako aplikační výstup na stdout, stderr, formáty příkazů, etc necháváme na vás. Pro stahování souborů můžete použít libovolnou knihovnu, ale blokující invokace příkazů wget/curl je taktéž naprosto v pořádku. Jinak používejte pouze moduly ze standardní knihovny C++, kód by měl být ideálně multiplatformní, ale za referenční prostředí považujte novější LTS distribuce Ubuntu, případě MacOS. Kompilátor apple-clang nebo clang ve verzi podporující C++20 a novější.

```
přepracuj a připrav toto zadání ve dvou variantách, tak, aby pro jedno zadání bylo vhodnější použít Message queue procesor a asynchronní job scheduling, a pro druhé zase aby byl lepší Visitor a kde by každý command byl vlastní silný typ, to by se pak dal pěkně aplikovat Visitor pattern na obsluhu commandů. Parser vstupu je pak dedikovaný modul (mimochodem, věděl byste jak jedním řádkem kódu nařezat string na vektor stringů? s std::ranges to jde krás
ně), factory na tvorbu Commandů je pak další modul.
v ani jednom zadání ale nespecifikuj požadavky na design - jen přesně popiš, co má požadovaná featura dělat, a nech kandidáta zvolit si postup sám.
Ideální by bylo, kdyby se tato dvě zadání krásně doplňovala - například řešení Visitorem by implementovalo klienta, řešení Message queue procesorem by implementovalo server
klient i server by měli sdílet stejné API schéma, například ve formě flatbuffers .fbs - DownloadRequest(url), DownloadResponse(sessionId),DownloadStatusRequest(SessionId),DownloadStatusResponse(status) atd. -  klient i server si vygenerují ze schématu vlastní typy objektů, např c++ class header, enum class atd. 
klient by pak třeba implementoval IRequestWriter + IResponseReader, server by implementoval IRequestReader + IResponseWriter

# Dvě varianty zadání: „WebGrab Client“ × „WebGrab Server“

Cílem je, aby každé zadání – aniž by přímo vnucovalo konkrétní návrhový vzor – přirozeně vedlo kandidáta k odlišnému způsobu zpracování příkazů:

* Zadání A (Client) je **interaktivní, v paměti drží strom silných typů příkazů** → návštěvník (Visitor) je nejpohodlnější.
* Zadání B (Server) je **asynchronní, staví na trvalé frontě a paralelním plánování jobů** → Message-Queue Processor je vhodnější.

Oba programy sdílejí stejné API schéma (FlatBuffers), takže se výborně doplňují: klient produkuje požadavky, server je konzumuje.

***

## 1. Zadání A – WebGrab Client (konzolový nástroj)

Naprogramujte v C++20 konzolovou aplikaci „webgrab-client“, která plní roli front-endového **klienta** pro službu WebGrab.  
Po spuštění čte příkazový řádek, zadané příkazy převádí na binární zprávy podle přiloženého FlatBuffers schématu `webgrab.fbs` a odesílá je na TCP socket (host:port předané parametry CLI).  
Klient uchovává lokální **frontu odchozích požadavků** s možností:

* `download <url>` – zařadí nový DownloadRequest.  
* `status <session-id>` – zařadí DownloadStatusRequest.  
* `abort  <session-id>` – zařadí DownloadAbortRequest.  
* `quit` – odešle ShutdownRequest a ukončí aplikaci.

Po přijetí odpovědi (DownloadResponse, DownloadStatusResponse, …) klient vytiskne stručné hlášení na stdout.

### Funkční požadavky

1. Příkazy lze řetězit interaktivně; zadání ignoruje prázdné řádky a komentáře `#`.
2. Odesílání i příjem probíhá **synchronně** – klient čeká na odpověď dřív, než přijme další vstup.
3. Klient musí validovat syntaxi URL a číselných ID dřív, než vytvoří binární zprávu.
4. Protokol transportu: délkově prefiksovaný rámec (uint32 network-byte-order + payload).
5. Koncové kódy návratového procesu: 0 = OK, ≠0 = chyba připojení nebo nevalidní vstup.

### Dodané artefakty

* `webgrab.fbs` – již obsahuje definice:
  ```
  table DownloadRequest   { url:string; }
  table DownloadResponse  { sessionId:uint32; }
  table DownloadStatusRequest  { sessionId:uint32; }
  table DownloadStatusResponse { status:string; }
  table DownloadAbortRequest   { sessionId:uint32; }
  table ShutdownRequest { }
  ```
* Build skript `CMakeLists.txt`.
* README s ukázkou použití.

***

## 2. Zadání B – WebGrab Server (vícevláknová služba)

Naprogramujte v C++20 vícevláknovou službu „webgrab-server“, která naslouchá na TCP socketu, přijímá binární zprávy ve formátu `webgrab.fbs` a dává je do vytrvalé **fronty úloh** (může být souborová, SQLite nebo externí MQ).  
Pracovní vlákna (2-4) čtou z fronty a zpracovávají úlohy:

* DownloadRequest   → stáhnout soubor na disk (libcurl nebo wget) a uložit mapu sessionId→stav.  
* DownloadStatusRequest → vrátit aktuální stav (Queued, Downloading, Completed, Failed, Aborted).  
* DownloadAbortRequest  → příznak zrušení; běžící download má povinnost co nejdřív skončit.  
* ShutdownRequest   → přijmout, ale zpracovat **až** fronta dosáhne prázdného stavu; pak korektně ukončit.

### Funkční požadavky

1. **Asynchronní** zpracování: přijetí zprávy se musí potvrdit klientovi okamžitě, skutečná práce probíhá na pozadí.
2. Fronta musí přežít restart procesu; nedokončené joby se po startu znovu zařadí.
3. Každý job má unikátní `sessionId` (uint32).  
4. Stavová data i soubory je potřeba ukládat do samostatného pracovního adresáře, jenž je zadán parametrem při spuštění.
5. Limity: paralelně nejvýš 4 downloads; ostatní čekají ve frontě.

### Dodané artefakty

* Stejné `webgrab.fbs` jako u klienta.  
* Build skript `CMakeLists.txt`.  
* README s pokyny k nasazení a příkladovým `systemd` service filem.

***

## Společné poznámky pro kandidáty

* Přiložené schéma FlatBuffers je jediným pevně daným API – implementační detaily, logování, testy a volba knihoven jsou na vás.  
* U klienta i serveru oceníme čisté oddělení **I/O** (socket, disk) od **doménové logiky**.  
* Připravte alespoň základní sadu jednotkových testů (GoogleTest nebo Catch2) a jednoduchý skript e2e-testu (`bash` nebo `Python`).

***

Díky tomuto rozdělení:

* **Client** (Visitor / strong-typed commands): důraz na typovou bezpečnost, synchronní logiku a pohodlné rozšiřování nových CLI příkazů.
* **Server** (Message Queue Processor): důraz na škálovatelnost, odolnost a paralelní scheduling dlouhotrvajících download úloh.

Kandidát si tak může zvolit nejvhodnější architekturu, přesto oba projekty spolu bezešvě komunikují díky sdílenému FlatBuffers schématu.

Citations:
[1] What is the difference between Strategy pattern and Visitor ... https://stackoverflow.com/questions/8665295/what-is-the-difference-between-strategy-pattern-and-visitor-pattern
[2] Event Queues vs Observers/Subjects in Entity Component ... https://www.reddit.com/r/gamedev/comments/65qhd0/event_queues_vs_observerssubjects_in_entity/
[3] Visitor design pattern https://www.geeksforgeeks.org/system-design/visitor-design-pattern/
[4] Visitor https://refactoring.guru/design-patterns/visitor
[5] Visitor Method Design Patterns in C++ https://www.geeksforgeeks.org/system-design/visitor-method-design-patterns-in-c/
[6] A Developer's Guide to Modern Queue Patterns https://dzone.com/articles/modern-queue-patterns-guide
[7] Ask HN: Why do message queue-based architectures ... https://news.ycombinator.com/item?id=40723302
[8] RabbitMQ Use cases: Explaining message queues and ... https://www.cloudamqp.com/blog/rabbitmq-use-cases-explaining-message-queues-and-when-to-use-them.html
[9] What is Message Queue? And what's it's use case? : r/csharp https://www.reddit.com/r/csharp/comments/166zz25/what_is_message_queue_and_whats_its_use_case/
[10] What are message queues? When to use them? https://www.contrastsecurity.com/security-influencers/what-is-a-message-queue-importance-use-cases-and-vulnerabilities-contrast-security
[11] Message Queue Use Cases and Patterns https://systemdesignschool.io/fundamentals/message-queue-use-cases
[12] Introduction to message queues and their key use cases https://upsun.com/blog/introduction-to-message-queues/
[13] Message Queues - System Design https://www.geeksforgeeks.org/system-design/message-queues-system-design/
[14] Introduction to Message Queues https://www.baeldung.com/cs/message-queues
[15] What Is a Message Queue? | IBM https://www.ibm.com/think/topics/message-queues
[16] Processing large amount of data using Queue Processor https://support.pega.com/question/processing-large-amount-data-using-queue-processor
[17] When should you really use the visitor pattern https://stackoverflow.com/questions/33456948/when-should-you-really-use-the-visitor-pattern
[18] r/java - Visitor Pattern Considered Pointless - Use ... https://www.reddit.com/r/java/comments/og6d72/visitor_pattern_considered_pointless_use_pattern/
[19] When should I use the Visitor Design Pattern? [closed] https://stackoverflow.com/questions/255214/when-should-i-use-the-visitor-design-pattern
[20] Is the visitor pattern bad for libraries with user-defined ... https://www.reddit.com/r/AskProgramming/comments/wjzb4v/is_the_visitor_pattern_bad_for_libraries_with/
[21] What is a message queue? https://www.dynatrace.com/news/blog/what-is-a-message-queue/
[22] The visitor pattern in C# — The Good, The Bad, And The Ugly https://www.dateo-software.de/blog/visitor-pattern
[23] Message Queues vs. Streaming Systems: Key Differences ... https://socprime.com/blog/message-queues-vs-streaming-systems-key-differences-and-use-cases/
[24] Visitor Pattern Considered Pointless - Use Pattern Switches ... https://nipafx.dev/java-visitor-pattern-pointless/
[25] Implementing Message Queuing https://cwoodruff.github.io/book-network-programming-csharp/chapter15/
[26] Message queues : The right way to process and transform ... https://ably.com/blog/message-queues-the-right-way
[27] Microservices communications. Why you should switch to ... https://dev.to/matteojoliveau/microservices-communications-why-you-should-switch-to-message-queues--48ia
[28] Understanding why you would want to process Message ... https://stackoverflow.com/questions/60350790/understanding-why-you-would-want-to-process-message-queues-at-a-future-time
[29] Choosing The Right Message Queue Technology For Your ... https://www.suprsend.com/post/choosing-the-right-message-queue-technology-for-your-notification-system
[30] Unlocking the potential of message queues https://developer.ibm.com/articles/awb-unlocking-potential-message-queues/
[31] Visitor Queue Integrations | Lead Generation Made Easy https://www.visitorqueue.com/integration
