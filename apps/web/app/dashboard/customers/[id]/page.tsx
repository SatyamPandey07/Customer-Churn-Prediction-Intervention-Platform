// Server component — required for generateStaticParams with output: 'export'
import CustomerDetailClient from './CustomerDetailClient';

export function generateStaticParams() {
  return [
    { id: 'cus_8f93a210-4b11-4a7b-8910-c119284fa901' },
    { id: 'cus_3c9210aa-7e12-4211-9012-d8123984fa02' },
    { id: 'cus_1b829402-9a01-4c12-8812-e7123948fa03' },
    { id: 'cus_5d910283-1192-4f22-9901-a6128492fa04' },
    { id: 'cus_7e102934-2283-4a11-8823-b5192840fa05' },
    { id: 'cus_9a102945-3394-4b22-9934-c4192851fa06' },
    { id: 'cus_2b102956-4405-4c33-1045-d3192862fa07' },
  ];
}

export default function CustomerDetailPage() {
  return <CustomerDetailClient />;
}
