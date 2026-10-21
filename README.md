Set-Content -Path .\README.md -Value @'
# Usługa Wypożyczalni Rowerów

Projekt zrealizowany w ramach laboratorium **LAB1 — Od problemu do własnej mikrousługi** w technologii **Python + FastAPI**.

## 1. Opis problemu i odpowiedzialność usługi (Bounded Context)
Usługa odpowiada za cykl życia fizycznych rowerów w systemie oraz ich stan rezerwacji.

*   **Usługa odpowiada za:**
    *   Przechowywanie bazy rowerów i ich aktualnych statusów w pamięci procesu.
    *   Weryfikację poprawności przejść stanów (egzekwowanie reguł biznesowych).
    *   Udostępnianie interfejsu HTTP/REST dla aplikacji klienckich do pobierania danych o rowerach i realizowania operacji wypożyczeń.
*   **Usługa NIE odpowiada za:**
    *   Naliczanie opłat minutowych za czas użytkowania oraz integrację z bramkami płatniczymi.
    *   Autoryzację użytkowników, weryfikację dokumentów tożsamości czy subskrypcje.
    *   Śledzenie współrzędnych GPS pojazdów w czasie rzeczywistym.

## 2. Podział systemu na usługi (Projekt Architektury)

| Usługa | Odpowiedzialność biznesowa | Własne dane | Operacje API | Informacje z innych usług |
| :--- | :--- | :--- | :--- | :--- |
| **Bike Rental Service** (LAB1) | Status i wypożyczenia rowerów. | Lista rowerów, ich stan (`free`/`rented`/`service`). | Dodanie roweru, odczyt stanu, zmiana statusu (wypożyczenie). | Brak - usługa w pełni autonomiczna dla swojej domeny. |
| **Payment Service** (Planowana) | Rozliczanie transakcji i pobieranie opłat. | Portfele użytkowników, cenniki, historia transakcji. | Obciążenie konta, weryfikacja środków. | Czas trwania wypożyczenia przekazany z `Bike Rental Service`. |

### Pojęcia domeny (Słownik)
1.  **Bike (Rower):** Kluczowy zasób posiadający unikalny identyfikator (np. `BIKE-01`), model oraz przypisany stan.
2.  **Status:** Stan w jakim znajduje się pojazd: `free` (dostępny), `rented` (wypożyczony) lub `service` (wyłączony z ruchu, w naprawie).
3.  **Rental (Wypożyczenie):** Akcja użytkownika skutkująca zablokowaniem roweru do użytku przez inne osoby.

### Szkic przyszłego kontraktu komunikacji (HTTP)
Gdy użytkownik kończy jazdę, `Bike Rental Service` (Nadawca) powiadomi `Payment Service` (Odbiorca) o konieczności naliczenia opłaty:
*   **Metoda:** `POST`
*   **Ścieżka:** `/payments/charge`
*   **Żądanie (JSON):** `{"user_id": "usr_99", "bike_id": "BIKE-01", "duration_minutes": 45}`
*   **Odpowiedź sukcesu (201):** `{"transaction_id": "tx_abc123", "status": "completed", "amount": 15.00}`
*   **Zachowanie przy awarii:** W przypadku niedostępności `Payment Service`, usługa `Bike Rental Service` zapisze zdarzenie zakończenia wypożyczenia lokalnie i ponowi próbę za pomocą kolejki wiadomości (np. RabbitMQ) po przywróceniu łączności.

---

## 3. Reguła Biznesowa
**Roweru o statusie `service` (w naprawie) ani `rented` (już wypożyczony) nie można wypożyczyć.**
*   *Przykład operacji dozwolonej:* Zmiana statusu z `free` na `rented` (Użytkownik podchodzi do wolnego roweru i go wypożycza).
*   *Przykład operacji niedozwolonej:* Zmiana statusu z `service` na `rented` (Próba wypożyczenia roweru, który mechanik zablokował w systemie jako uszkodzony).
*   *Oczekiwany kod błędu:* **409 Conflict** przy próbie naruszenia reguły.

---

## 4. Kontrakt API i Obsługa Błędów

### Wykaz endpointów
*   **GET** `/health` - Zwraca stan działania aplikacji (`200 OK`).
*   **GET** `/bikes` - Lista wszystkich rowerów (`200 OK`, zwraca pustą tablicę `[]`, jeśli brak zasobów).
*   **GET** `/bikes/{bike_id}` - Szczegóły jednego roweru (`200 OK` lub `404 Not Found`).
*   **PATCH** `/bikes/{bike_id}/status` - Zmiana statusu / wypożyczenie (`200 OK`, `404 Not Found`, `409 Conflict` lub `422 Unprocessable Entity`).

### Przykłady struktur JSON

#### Sukces (PATCH /bikes/BIKE-01/status z body `{"status": "rented"}`)
```json
{
  "id": "BIKE-01",
  "model": "Veturilo Standard",
  "status": "rented"
}
```

#### Błąd 404 (Nieistniejący rower)
```json
{
  "detail": "Nie znaleziono roweru o podanym ID."
}
```

#### Błąd 409 (Naruszenie reguły biznesowej)
```json
{
  "detail": "Nie można wypożyczyć roweru, który aktualnie znajduje się w naprawie (status: service)."
}
```

#### Błąd 422 (Niepoprawny status - walidacja wartości)
```json
{
  "detail": "Nieprawidłowy status. Dozwolone to: ['free', 'rented', 'service']"
}
```

---

## 5. Instrukcja uruchomienia i testów

### Uruchomienie aplikacji
```powershell
# Utworzenie i aktywacja środowiska (jeśli wymagane)
python -m venv .venv
# Instalacja zależności
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn pytest httpx
# Start serwera deweloperskiego
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8101
```
Aplikacja jest dostępna pod adresem: `http://localhost:8101`
Dokumentacja interaktywna Swagger UI: `http://localhost:8101/docs`

### Uruchomienie testów automatycznych
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

---

## 6. Wyniki eksperymentu z restartem procesu
1. Wykonano modyfikację statusu roweru `BIKE-01` z `free` na `rented` za pomocą metody PATCH. Osobnym żądaniem GET zweryfikowano pomyślne zapisanie stanu w słowniku.
2. Proces serwera Uvicorn został zatrzymany w konsoli za pomocą kombinacji `Ctrl + C`.
3. Po ponownym uruchomieniu serwera, ponowne wykonanie żądania GET wykazało, że stan roweru powrócił do wartości fabrycznej (`free`).

**Wniosek:** Wynika to z faktu, że baza danych została zaimplementowana w pamięci RAM procesu aplikacji (`In-Memory Dictionary`). Zatrzymanie procesu powoduje całkowite zwolnienie pamięci przez system operacyjny. Ponowny rozruch skutkuje wykonaniem funkcji fabrykującej od początku i załadowaniem domyślnego słownika startowego.

---

## 7. Wykorzystanie Oficjalnej Dokumentacji (EK_03)
1. **Walidacja struktur za pomocą Pydantic `Field`**
   * *Źródło:* https://pydantic.dev
   * *Zastosowanie:* Ograniczenie długości identyfikatora roweru (`min_length=3`, `max_length=10`) bezpośrednio w schemacie wejściowym, zapobiegając przesyłaniu pustych lub zbyt długich ciągów znaków.
2. **Obsługa błędów za pomocą `HTTPException` w FastAPI**
   * *Źródło:* https://tiangolo.com
   * *Zastosowanie:* Wykorzystanie klasy wyjątków FastAPI do natychmiastowego przerwania przetwarzania żądania i zwrócenia ujednoliconej struktury błędu z odpowiednim kodem HTTP (np. 404 lub 409).