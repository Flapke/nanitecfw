# T-Engine

Source: https://github.com/raywan/tengine
Revision: 0146b3bf9e65e3b7e1976ac501f81e44d9cf1dce
License: MIT; see LICENSE. The notice is also embedded in the game payload.

Local embedded adaptations:

- Replace the 5,040-permutation table with a Fisher-Yates seven-piece bag.
- Let the platform seed the random generator.
- Clip writes for pieces partly above the board.
- Honor the update frame delta, allowing redraws without advancing gravity.

The firmware wrapper supplies two fixed board buffers instead of a general heap.