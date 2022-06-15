update ir_ui_view 
set arch_db='<?xml version="1.0"?>
<field name="name" position="after">
                <field name="product_id" string="Libro"/>
                <field name="collana_id" string="Collana"/>
                <field name="street2" string="Testata" filter_domain="[(''street2'',''ilike'',self)]"/>
                <field name="comment" string="Note"/>
            </field>'
where arch_db like '%Libro%';


update ir_ui_view 
set arch_prev='<?xml version="1.0"?>
<field name="name" position="after">
                <field name="product_id" string="Libro"/>
                <field name="collana_id" string="Collana"/>
                <field name="street2" string="Testata" filter_domain="[(''street2'',''ilike'',self)]"/>
                <field name="comment" string="Note"/>
            </field>'
where arch_db like '%Libro%';


update ir_ui_view
set arch_db='<?xml version="1.0"?>
<search string="Search Partner">
                    <field name="name" filter_domain="[''|'', ''|'', (''display_name'', ''ilike'', self), (''ref'', ''='', self), (''email'', ''ilike'', self)]"/>
                    <field name="parent_id" domain="[(''is_company'', ''='', True)]" operator="child_of"/>
                    <field name="email" filter_domain="[(''email'', ''ilike'', self)]"/>
                    <field name="phone" filter_domain="[''|'', (''phone'', ''ilike'', self), (''mobile'', ''ilike'', self)]"/>
                    <field name="category_id" string="Tag" filter_domain="[(''category_id'', ''child_of'', self)]"/>
                    <field name="user_id"/>
                    <separator/>
                    <filter string="Individuals" name="type_person" domain="[(''is_company'', ''='', False)]"/>
                    <filter string="Companies" name="type_company" domain="[(''is_company'', ''='', True)]"/>
                    <separator/>
                    <filter string="Archived" name="inactive" domain="[(''active'', ''='', False)]"/>
                    <separator/>
                    <group expand="0" name="group_by" string="Group By">
                        <filter name="salesperson" string="Salesperson" domain="[]" context="{''group_by'' : ''user_id''}"/>
                        <filter name="group_company" string="Company" context="{''group_by'': ''parent_id''}"/>
                        <filter name="group_country" string="Country" context="{''group_by'': ''country_id''}"/>
                    </group>
                </search>
				'
where id=125;

update ir_ui_view
set 
    create_uid = 1,
    active = true
where id=815;



            