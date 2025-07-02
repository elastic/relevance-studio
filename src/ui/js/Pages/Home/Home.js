import { useEffect, useState } from 'react'
import {
  EuiButton,
  EuiCode,
  EuiEmptyPrompt,
  EuiPanel,
  EuiProgress,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { Page } from '../../Layout'
import { getHistory } from '../../history'
import api from '../../api'

const Home = () => {

  const history = getHistory()

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, isSetup, setIsSetup } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [isProcessing, setIsProcessing] = useState(false)

  ////  Effects  ///////////////////////////////////////////////////////////////

  // Redirect if setup is complete
  useEffect(() => {
    if (isSetup === true) {
      history.push('/projects')
    }
  }, [isSetup])

  ////  Handlers  //////////////////////////////////////////////////////////////

  const onSetup = async () => {
    try {
      setIsProcessing(true)
      const response = await api.setup_run()

      if ((response?.data?.failures ?? 0) === 0) {
        setIsSetup(true)
        addToast({ color: 'success', title: 'Setup complete!' })
        history.push('/projects')
      } else {
        setIsSetup(false)
        addToast({
          color: 'danger',
          title: 'Setup incomplete',
          text: (
            <EuiText size='xs' color='subdued'>
              Failed to setup one or more index templates or indices.
            </EuiText>
          ),
        })
      }
    } catch (e) {
      addToast(api.errorToast(e, { title: 'Failed to run setup' }))
      setIsSetup(false)
    } finally {
      setIsProcessing(false)
    }
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  if (isSetup === null)
    return <EuiProgress color='accent' position='fixed' size='s' />

  return (
    <Page panelled title='Elasticsearch Relevance Studio'>
      <EuiPanel color='transparent'>
        <EuiEmptyPrompt
          color='plain'
          iconType='logoElasticsearch'
          title={<h2>Welcome!</h2>}
          body={<p>You're almost ready. Just click setup to finish.</p>}
          actions={
            <EuiButton
              color='primary'
              disabled={isProcessing}
              fill
              isLoading={isProcessing}
              onClick={onSetup}
            >
              Setup
            </EuiButton>
          }
          footer={
            <EuiText size='s'>
              This will create the <EuiCode style={{ padding: 0 }} transparentBackground>esrs-*</EuiCode> index templates and indices.
            </EuiText>
          }
        />
      </EuiPanel>
    </Page>
  )
}

export default Home