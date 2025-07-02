export class SetupIncompleteError extends Error {
  constructor(message = 'Setup incomplete') {
    super(message)
    this.name = 'SetupIncompleteError'
  }
}