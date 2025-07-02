/**
 * Custom global history object that can be used both inside and outside
 * React components, unlike useHistory from react-router-dom.
 */
import { createHashHistory } from 'history'
const history = createHashHistory()

export default history
export const getHistory = () => history