# MAI-z micropython lib

This project contains a micropython library to interact with the MAI-z robot. It is based on the official [MakeCode library](https://github.com/KitronikLtd/pxt-kitronik-mai-z/blob/master/Mai-Z.ts) and is designed to be used with the [MAI-z robot](https://www.kitronik.co.uk/5650-kitronik-mai-z-robot). There is no official micropython library for the MAI-z robot, so I hope this project will be useful for anyone who wants to use the MAI-z robot with micropython.

## Usage

Copy the `mai_z.py` file into the root of your project and import it in your code:

```python
import mai_z

mai_z.move(mai_z.MoveDirection.FORWARDS, speed=50, distance=mai_z.MoveDistance.CONTINUOUS)
```

See `main.py` for a full example of how to use the library.
