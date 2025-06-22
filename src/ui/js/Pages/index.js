import { Benchmarks } from './Benchmarks'
import { BenchmarksView } from './BenchmarksView'
import { Displays } from './Displays'
import { DisplaysEdit } from './DisplaysEdit'
import { EvaluationsView } from './EvaluationsView'
import { Home } from './Home'
import { Judgements } from './Judgements'
import { Projects } from './Projects'
import { Scenarios } from './Scenarios'
import { Strategies } from './Strategies'
import { StrategiesEdit } from './StrategiesEdit'

const Pages = ({ children }) => <>{children}</>

Pages.Benchmarks = Benchmarks
Pages.BenchmarksView = BenchmarksView
Pages.Displays = Displays
Pages.DisplaysEdit = DisplaysEdit
Pages.EvaluationsView = EvaluationsView
Pages.Home = Home
Pages.Judgements = Judgements
Pages.Projects = Projects
Pages.Scenarios = Scenarios
Pages.Strategies = Strategies
Pages.StrategiesEdit = StrategiesEdit

export { Pages }