/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { Benchmarks } from './Benchmarks'
import { BenchmarksView } from './BenchmarksView'
import { Displays } from './Displays'
import { DisplaysEdit } from './DisplaysEdit'
import { EvaluationsView } from './EvaluationsView'
import { Home } from './Home'
import { Judgements } from './Judgements'
import { NotFound } from './NotFound'
import { Scenarios } from './Scenarios'
import { Strategies } from './Strategies'
import { StrategiesEdit } from './StrategiesEdit'
import { Workspaces } from './Workspaces'
import { WorkspacesCreate } from './WorkspacesCreate'
import { WorkspacesView } from './WorkspacesView'

const Pages = ({ children }) => <>{children}</>

Pages.Benchmarks = Benchmarks
Pages.BenchmarksView = BenchmarksView
Pages.Displays = Displays
Pages.DisplaysEdit = DisplaysEdit
Pages.EvaluationsView = EvaluationsView
Pages.Home = Home
Pages.Judgements = Judgements
Pages.NotFound = NotFound
Pages.Scenarios = Scenarios
Pages.Strategies = Strategies
Pages.StrategiesEdit = StrategiesEdit
Pages.Workspaces = Workspaces
Pages.WorkspacesCreate = WorkspacesCreate
Pages.WorkspacesView = WorkspacesView

export { Pages }