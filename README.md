# Bike Rental Service (Us�uga Wypo�yczalni Rower�w)

Projekt zrealizowany w ramach laboratorium **LAB1 � Od problemu do w�asnej mikrous�ugi** w technologii **Python + FastAPI**.

## 1. Opis problemu i odpowiedzialno�� us�ugi (Bounded Context)
Us�uga odpowiada za cykl �ycia fizycznych rower�w w systemie oraz ich stan rezerwacji.

*   **Us�uga odpowiada za:**
    *   Przechowywanie bazy rower�w i ich aktualnych status�w w pami�ci procesu.
    *   Weryfikacj� poprawno�ci przej�� stan�w (egzekwowanie regu� biznesowych).
    *   Udost�pnianie interfejsu HTTP/REST dla aplikacji klienckich do pobierania danych o rowerach i realizowania operacji wypo�ycze�.
*   **Us�uga NIE odpowiada za:**
    *   Naliczanie op�at minutowych za czas u�ytkowania oraz integracj� z bramkami p�atniczymi.
    *   Autoryzacj� u�ytkownik�w, weryfikacj� dokument�w to�samo�ci czy subskrypcje.
    *   �ledzenie wsp�rz�dnych GPS pojazd�w w czasie rzeczywistym.

## 2. Podzia� systemu na us�ugi (Projekt Architektury)

| Us�uga | Odpowiedzialno�� biznesowa | W�asne dane | Operacje API | Informacje z innych us�ug |
| :--- | :--- | :--- | :--- | :--- |
| **Bike Rental Service** (LAB1) | Status i wypo�yczenia rower�w. | Lista rower�w, ich stan (`free`/`rented`/`service`). | Dodanie roweru, odczyt stanu, zmiana statusu (wypo�yczenie). | Brak - us�uga w pe�ni autonomiczna dla swojej domeny. |
| **Payment Service** (Planowana) | Rozliczanie transakcji i pobieranie op�at. | Portfele u�ytkownik�w, cenniki, historia transakcji. | Obci��enie konta, weryfikacja �rodk�w. | Czas trwania wypo�yczenia przekazany z `Bike Rental Service`. |

### Poj�cia domeny (S�ownik)
1.  **Bike (Rower):** Kluczowy zas�b posiadaj�cy unikalny identyfikator (np. `BIKE-01`), model oraz przypisany stan.
2.  **Status:** Stan w jakim znajduje si� pojazd: `free` (dost�pny), `rented` (wypo�yczony) lub `service` (wy��czony z ruchu, w naprawie).
3.  **Rental (Wypo�yczenie):** Akcja u�ytkownika skutkuj�ca zablokowaniem roweru do u�ytku przez inne osoby.

### Szkic przysz�ego kontraktu komunikacji (HTTP)
Gdy u�ytkownik ko�czy jazd�, `Bike Rental Service` (Nadawca) powiadomi `Payment Service` (Odbiorca) o konieczno�ci naliczenia op�aty:
*   **Metoda:** `POST`
*   **�cie�ka:** `/payments/charge`
*   **��danie (JSON):** `{"user_id": "usr_99", "bike_id": "BIKE-01", "duration_minutes": 45}`
*   **Odpowied� sukcesu (201):** `{"transaction_id": "tx_abc123", "status": "completed", "amount": 15.00}`
*   **Zachowanie przy awarii:** W przypadku niedost�pno�ci `Payment Service`, us�uga `Bike Rental Service` zapisze zdarzenie zako�czenia wypo�yczenia lokalnie i ponowi pr�b� za pomoc� kolejki wiadomo�ci (np. RabbitMQ) po przywr�ceniu ��czno�ci.

---

## 3. Regu�a Biznesowa
**Roweru o statusie `service` (w naprawie) ani `rented` (ju� wypo�yczony) nie mo�na wypo�yczy�.**
*   *Przyk�ad operacji dozwolonej:* Zmiana statusu z `free` na `rented` (U�ytkownik podchodzi do wolnego roweru i go wypo�ycza).
*   *Przyk�ad operacji niedozwolonej:* Zmiana statusu z `service` na `rented` (Pr�ba wypo�yczenia roweru, kt�ry mechanik zablokowa� w systemie jako uszkodzony).
*   *Oczekiwany kod b��du:* **409 Conflict** przy pr�bie naruszenia regu�y.

---

## 4. Kontrakt API i Obs�uga B��d�w

### Wykaz endpoint�w
*   **GET** `/health` - Zwraca stan dzia�ania aplikacji (`200 OK`).
*   **GET** `/bikes` - Lista wszystkich rower�w (`200 OK`, zwraca pust� tablic� `[]`, je�li brak zasob�w).
*   **GET** `/bikes/{bike_id}` - Szczeg�y jednego roweru (`200 OK` lub `404 Not Found`).
*   **PATCH** `/bikes/{bike_id}/status` - Zmiana statusu / wypo�yczenie (`200 OK`, `404 Not Found`, `409 Conflict` lub `422 Unprocessable Entity`).

### Przyk�ady struktur JSON

#### Sukces (PATCH /bikes/BIKE-01/status z body `{"status": "rented"}`)
```json
{
  "id": "BIKE-01",
  "model": "Veturilo Standard",
  "status": "rented"
}
```

#### B��d 404 (Nieistniej�cy rower)
```json
{
  "detail": "Nie znaleziono roweru o podanym ID."
}
```

#### B��d 409 (Naruszenie regu�y biznesowej)
```json
{
  "detail": "Nie mo�na wypo�yczy� roweru, kt�ry aktualnie znajduje si� w naprawie (status: service)."
}
```

#### B��d 422 (Niepoprawny status - walidacja warto�ci)
```json
{
  "detail": "Nieprawid�owy status. Dozwolone to: ['free', 'rented', 'service']"
}
```

---

## 5. Instrukcja uruchomienia i test�w

### Uruchomienie aplikacji
```powershell
# Utworzenie i aktywacja �rodowiska (je�li wymagane)
python -m venv .venv
# Instalacja zale�no�ci
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn pytest httpx
# Start serwera deweloperskiego
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8101
```
Aplikacja jest dost�pna pod adresem: `http://localhost:8101`
Dokumentacja interaktywna Swagger UI: `http://localhost:8101/docs`

### Uruchomienie test�w automatycznych
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

---

## 6. Wyniki eksperymentu z restartem procesu
1. Wykonano modyfikacj� statusu roweru `BIKE-01` z `free` na `rented` za pomoc� metody PATCH. Osobnym ��daniem GET zweryfikowano pomy�lne zapisanie stanu w s�owniku.
2. Proces serwera Uvicorn zosta� zatrzymany w konsoli za pomoc� kombinacji `Ctrl + C`.
3. Po ponownym uruchomieniu serwera, ponowne wykonanie ��dania GET wykaza�o, �e stan roweru powr�ci� do warto�ci fabrycznej (`free`).

**Wniosek:** Wynika to z faktu, �e baza danych zosta�a zaimplementowana w pami�ci RAM procesu aplikacji (`In-Memory Dictionary`). Zatrzymanie procesu powoduje ca�kowite zwolnienie pami�ci przez system operacyjny. Ponowny rozruch skutkuje wykonaniem funkcji fabrykuj�cej od pocz�tku i za�adowaniem domy�lnego s�ownika startowego.

---

## 7. Wykorzystanie Oficjalnej Dokumentacji (EK_03)
1. **Walidacja struktur za pomoc� Pydantic `Field`**
   * *�r�d�o:* https://pydantic.dev
   * *Zastosowanie:* Ograniczenie d�ugo�ci identyfikatora roweru (`min_length=3`, `max_length=10`) bezpo�rednio w schemacie wej�ciowym, zapobiegaj�c przesy�aniu pustych lub zbyt d�ugich ci�g�w znak�w.
2. **Obs�uga b��d�w za pomoc� `HTTPException` w FastAPI**
   * *�r�d�o:* https://tiangolo.com
   * *Zastosowanie:* Wykorzystanie klasy wyj�tk�w FastAPI do natychmiastowego przerwania przetwarzania ��dania i zwr�cenia ujednoliconej struktury b��du z odpowiednim kodem HTTP (np. 404 lub 409).