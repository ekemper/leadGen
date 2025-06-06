import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import SignIn from "./pages/AuthPages/SignIn";
import SignUp from "./pages/AuthPages/SignUp";
import NotFound from "./pages/OtherPage/NotFound";
import UserProfiles from "./pages/UserProfiles";
import Videos from "./pages/UiElements/Videos";
import Images from "./pages/UiElements/Images";
import Alerts from "./pages/UiElements/Alerts";
import Badges from "./pages/UiElements/Badges";
import Avatars from "./pages/UiElements/Avatars";
import Buttons from "./pages/UiElements/Buttons";
import LineChart from "./pages/Charts/LineChart";
import BarChart from "./pages/Charts/BarChart";
import Calendar from "./pages/Calendar";
import BasicTables from "./pages/Tables/BasicTables";
import FormElements from "./pages/Forms/FormElements";
import Blank from "./pages/Blank";
import AppLayout from "./layout/AppLayout";
import { ScrollToTop } from "./components/common/ScrollToTop";
import Home from "./pages/Dashboard/Home";
import CampaignsList from "./pages/CampaignsList";
import CampaignDetail from "./pages/CampaignDetail";
import OrganizationsList from "./pages/OrganizationsList";
import OrganizationDetail from "./pages/OrganizationDetail";
import OrganizationCreatePage from "./pages/OrganizationCreate";
import QueueMonitoring from "./pages/QueueMonitoring";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { ErrorProvider } from "./context/ErrorContext";
import { NetworkProvider } from "./context/NetworkContext";
import ErrorBoundary from "./components/common/ErrorBoundary";
import ErrorDisplay from "./components/common/ErrorDisplay";
import NetworkStatus from "./components/common/NetworkStatus";
import { logger } from './utils/logger';

// Initialize logger
logger;

export default function App() {
  return (
    <ErrorBoundary context="App Root" showDetails={process.env.NODE_ENV === 'development'}>
      <ErrorProvider>
        <NetworkProvider>
          <AuthProvider>
            <Router>
              <ScrollToTop />
              <Routes>
                {/* Auth Routes - Not Protected */}
                <Route path="/signin" element={<SignIn />} />
                <Route path="/signup" element={<SignUp />} />

                {/* Protected Routes */}
                <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
                  {/* Redirect root to dashboard */}
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Home />} />

                  {/* Others Page */}
                  <Route path="/profile" element={<UserProfiles />} />
                  <Route path="/calendar" element={<Calendar />} />
                  <Route path="/blank" element={<Blank />} />

                  {/* Forms */}
                  <Route path="/form-elements" element={<FormElements />} />

                  {/* Tables */}
                  <Route path="/basic-tables" element={<BasicTables />} />

                  {/* Ui Elements */}
                  <Route path="/alerts" element={<Alerts />} />
                  <Route path="/avatars" element={<Avatars />} />
                  <Route path="/badge" element={<Badges />} />
                  <Route path="/buttons" element={<Buttons />} />
                  <Route path="/images" element={<Images />} />
                  <Route path="/videos" element={<Videos />} />

                  {/* Charts */}
                  <Route path="/line-chart" element={<LineChart />} />
                  <Route path="/bar-chart" element={<BarChart />} />

                  {/* Campaigns */}
                  <Route path="/campaigns" element={<CampaignsList />} />
                  <Route path="/campaigns/:id" element={<CampaignDetail />} />

                  {/* Organizations */}
                  <Route path="/organizations" element={<OrganizationsList />} />
                  <Route path="/organizations/create" element={<OrganizationCreatePage />} />
                  <Route path="/organizations/:id" element={<OrganizationDetail />} />

                  {/* Queue Monitoring */}
                  <Route path="/queue-monitoring" element={<QueueMonitoring />} />
                </Route>

                {/* Fallback Route */}
                <Route path="*" element={<NotFound />} />
              </Routes>
              
              {/* Global UI Components */}
              <ErrorDisplay />
              <NetworkStatus />
            </Router>
          </AuthProvider>
        </NetworkProvider>
      </ErrorProvider>
    </ErrorBoundary>
  );
}
