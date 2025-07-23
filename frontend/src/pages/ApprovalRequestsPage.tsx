import React from 'react';
import { ApprovalRequestList } from '../components/approval';

const ApprovalRequestsPage: React.FC = () => {
  return (
    <ApprovalRequestList
      title="All Approval Requests"
      showFilters={true}
      showBulkActions={true}
      variant="default"
    />
  );
};

export default ApprovalRequestsPage;