/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License;
 * you may not use this file except in compliance with the Elastic License.
 */

/**
 * Custom global history object that can be used both inside and outside
 * React components, unlike useHistory from react-router-dom.
 */
import { createHashHistory } from 'history'
const history = createHashHistory()

export default history
export const getHistory = () => history