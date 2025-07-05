import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useAppContext } from './AppContext'
import api from '../api'

export const ProjectContext = createContext()
export const useProjectContext = () => useContext(ProjectContext)

export const ProjectProvider = ({ children }) => {

  /**
   * projectId comes from the URL path: /projects/:project_id
   */
  const { project_id: projectId } = useParams()

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, isSetup } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [project, setProject] = useState(null)
  const [isLoadingProject, setIsLoadingProject] = useState(false)
  const isProjectReady = project && !isLoadingProject

  ////  Loaders  ///////////////////////////////////////////////////////////////

  /**
   * Load project when projectId changes, which happens when we navigate
   * to a URL starting with /projects/:project_id
   */
  const loadProject = useCallback(async () => {
    if (isSetup === null)
      return
    if (isSetup === false) {
      window.location.href = '/#/'
      throw new Error(`Setup isn't complete`)
    }
    setIsLoadingProject(true)
    try {
      const response = await api.projects_get(projectId)
      const _project = response.data._source
      _project._id = response.data._id
      setProject(_project)
    } catch (e) {
      return addToast(api.errorToast(e, { title: `Failed to load project: ${projectId}` }))
    } finally {
      setIsLoadingProject(false)
    }
  }, [projectId, isSetup])

  /**
   * Automatically load the project data when the ProjectProvider mounts
   * or when the projectId in the URL changes (e.g. navigating between projects).
   */
  useEffect(() => {
    const run = async () => {
      await loadProject()
    }
    run()
  }, [loadProject])

  return (
    <ProjectContext.Provider value={{ project, isLoadingProject, isProjectReady }}>
      {children}
    </ProjectContext.Provider>
  )
}