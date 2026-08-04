import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta

from apps.api.core.deps import engine
from apps.api.models import Customer, CustomerEvent, PlanTier, Tenant
from sqlalchemy import text

# Setup DB session
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def generate_data(num_customers=200):
    async with AsyncSessionLocal() as session:
        # 1. Create a dummy tenant
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            name="Synthetic Data Corp",
            subdomain=f"synthetic-{str(tenant_id)[:8]}",
            plan_tier=PlanTier.tier1,
        )
        session.add(tenant)
        await session.commit()
        
        # Enable RLS for this session
        await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

        print(f"Created Tenant {tenant_id}")
        
        end_date = datetime.now(UTC)
        
        for i in range(num_customers):
            is_churner = (i < num_customers // 2)
            customer_id = uuid.uuid4()
            start_date = end_date - timedelta(days=90)
            
            customer = Customer(
                id=customer_id,
                tenant_id=tenant_id,
                external_ids={"stripe": f"cus_{customer_id}"},
                plan="premium" if random.random() > 0.5 else "basic",
                mrr=50.0 if not is_churner else 20.0,
                created_at=start_date,
                first_seen_at=start_date,
                last_seen_at=end_date if not is_churner else end_date - timedelta(days=5),
            )
            session.add(customer)
            
            # Generate 90 days of events
            current_date = start_date
            seat_count = 10
            
            while current_date < end_date:
                days_to_end = (end_date - current_date).days
                
                # Activity probabilities
                login_prob = 0.8
                ticket_prob = 0.05
                payment_fail_prob = 0.01
                
                if is_churner:
                    # Deteriorating health as we get closer to end_date (churn)
                    if days_to_end < 30:
                        login_prob = 0.2
                        ticket_prob = 0.3
                        payment_fail_prob = 0.2
                        if random.random() < 0.1:
                            seat_count = max(1, seat_count - 1)
                    elif days_to_end < 60:
                        login_prob = 0.5
                        ticket_prob = 0.15
                else:
                    # Healthy usage
                    if random.random() < 0.05:
                        seat_count += 1
                
                if random.random() < login_prob:
                    event = CustomerEvent(
                        tenant_id=tenant_id, customer_id=customer_id,
                        source="segment", external_event_id=str(uuid.uuid4()),
                        event_type="page_view", properties={}, occurred_at=current_date
                    )
                    session.add(event)
                    
                    event = CustomerEvent(
                        tenant_id=tenant_id, customer_id=customer_id,
                        source="segment", external_event_id=str(uuid.uuid4()),
                        event_type="feature_used", properties={"feature": "reports"}, occurred_at=current_date
                    )
                    session.add(event)
                    
                if random.random() < ticket_prob:
                    event = CustomerEvent(
                        tenant_id=tenant_id, customer_id=customer_id,
                        source="zendesk", external_event_id=str(uuid.uuid4()),
                        event_type="ticket_created", properties={"priority": "high"}, occurred_at=current_date
                    )
                    session.add(event)
                    
                if random.random() < payment_fail_prob:
                    event = CustomerEvent(
                        tenant_id=tenant_id, customer_id=customer_id,
                        source="stripe", external_event_id=str(uuid.uuid4()),
                        event_type="invoice.failed", properties={}, occurred_at=current_date
                    )
                    session.add(event)
                    
                # Weekly subscription sync
                if current_date.weekday() == 0:
                    event = CustomerEvent(
                        tenant_id=tenant_id, customer_id=customer_id,
                        source="stripe", external_event_id=str(uuid.uuid4()),
                        event_type="subscription_updated", properties={"seat_count": seat_count}, occurred_at=current_date
                    )
                    session.add(event)
                
                current_date += timedelta(days=1)
                
            if is_churner:
                event = CustomerEvent(
                    tenant_id=tenant_id, customer_id=customer_id,
                    source="stripe", external_event_id=str(uuid.uuid4()),
                    event_type="subscription_canceled", properties={}, occurred_at=end_date
                )
                session.add(event)
                
            if i % 10 == 0:
                print(f"Generated {i} customers...")
                await session.commit()
                # Restore RLS after commit
                await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
                
        await session.commit()
        print(f"Successfully generated {num_customers} synthetic customers for tenant {tenant_id}")
        return tenant_id

if __name__ == "__main__":
    asyncio.run(generate_data())
