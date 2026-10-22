# SkyBound Airlines

A command-line airline booking program. Passengers can search flights, reserve seats, view tickets, and track bookings. Administrators can manage flights and view reports.

## Run the program

From this folder, run:

```powershell
python main.py
```

Choose `1` to sign in or `2` to create an account. On a new sample database, you can try the passenger demo account:

- Username: `demo`
- Password: `demo123`

## Passenger: book a flight

1. At the start menu, choose `1` and sign in, or choose `2` to register.
2. Search for a route, for example:

   ```text
   search RUH JED
   ```

   Use `airports` to see airport codes. Search results show Flight IDs; choose one from the list.
3. Start a booking with that Flight ID:

   ```text
   book SB1001
   ```

   For a connecting trip, enter both Flight IDs in order: `book SB1001 SB1002`.
4. Follow the numbered prompts: enter the passenger count and names, choose a seat for each passenger (`auto` selects the first available economy seat), then review the total and answer `y` to confirm.
5. Save the booking reference shown on the receipt. Use it to view details later:

   ```text
   mybookings
   booking SBXXXXX
   ticket SBXXXXX
   ```

At an input prompt, type `cancel` to abandon that step. Type `help` at the command prompt to see all available commands, or `logout` to return to the start menu.

## Other passenger commands

- `calendar RUH JED` — compare fares by day.
- `recommend` — view trip suggestions.
- `status SB1001` — check a flight, or use your booking reference to check a booking.
- `cancel SBXXXXX` — cancel a booking and review the refund before confirming.
- `flights` — list upcoming flights.

## Administrator commands

Sign in with an administrator account, then type `help` to see the available commands. Common tasks:

- `flights` — list flights.
- `addflight` — follow the prompts to create a flight.
- `delay SB1001 30` — set a flight delay in minutes.
- `manifest SB1001` — view passengers on a flight.
- `report` — view booking and revenue totals.

## Tests

From this folder, run:

```powershell
python -m unittest discover -s skybound\tests -v
```
