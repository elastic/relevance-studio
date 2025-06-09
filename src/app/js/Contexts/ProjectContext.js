import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react'
import { useLocation } from 'react-router-dom'
import { useAppContext } from './AppContext'
import api from '../api'

export const ProjectContext = createContext()

export const useProjectContext = () => useContext(ProjectContext)

export const ProjectProvider = ({ children }) => {

  const location = useLocation()

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [project, setProject] = useState(null)
  const [loadingProject, setLoadingProject] = useState(false)

  /**
   * Get project context on pages that have a project ID
   */
  useEffect(() => {
    (async () => {
      const match = location.pathname.match(/\/projects\/([^\/\#\?]+)/)
      const project_id = match ? match[1] : null;
      if (!project_id) {
        setProject(null)
        setLoadingProject(false)
        return
      }
      if (project_id !== project?._id) {

        // Submit API request
        let response
        try {
          setLoadingProject(true)
          response = await api.get_project(project_id)
        } catch (error) {
          return addToast(api.errorToast(error, {
            title: 'Failed to get project'
          }))
        } finally {
          setLoadingProject(false)
        }

        // Handle API response
        const _project = response.data._source
        _project._id = response.data._id
        setProject(_project)
      }
    })()
  }, [location])

  const value = useMemo(() => ({
    project,
    loadingProject,
  }), [project, loadingProject])

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  )
}